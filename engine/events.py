"""Sự kiện thế giới: phục tô, quỷ xuất hiện, phong tỏa, khẩn cấp, toàn máy chủ, giới hạn thời gian, nhiều kết cục."""
from __future__ import annotations

from core.errors import GameError
from core.util import wchoice
from data.events import CONTRIB_ACTIONS, EVENT_DEFS, STORIES, STORY_BY_ITEM
from data.ghosts import GHOSTS
from data.locations import HUB, LOCATIONS
from engine.economy import apply_effects
from engine.players import Service

DECAY_SECONDS = 6 * 3600
MAX_ACTIVE_CONTRIB = 2
TEAM_SIZE, TEAM_BONUS = 3, 1       # đội hình từ 3 người: +1 đóng góp mỗi hành động


class EventService(Service):
    def __init__(self, game):
        super().__init__(game)
        self._ann: list[dict] = []

    def announce(self, kind, event_id, title, text):
        self._ann.append({"kind": kind, "event_id": event_id, "title": title, "text": text})

    def drain_announcements(self) -> list[dict]:
        out, self._ann = self._ann, []
        return out

    # ---- truy vấn ---------------------------------------------------------------
    def get(self, event_id):
        r = self.db.one("SELECT * FROM world_events WHERE id=?", (event_id,))
        if not r:
            raise GameError("Không tìm thấy sự kiện này.")
        return r

    def active(self):
        return self.db.all("SELECT * FROM world_events WHERE state='active' AND ends_at>? ORDER BY ends_at",
                           (self.clock.now(),))

    def participants(self, event_id):
        return self.db.all("SELECT user_id,contribution FROM event_participants WHERE event_id=? "
                           "ORDER BY contribution DESC, user_id", (event_id,))

    # ---- tạo sự kiện ------------------------------------------------------------------
    def start_event(self, def_id, location_id=None, ghost_instance_id=None, duration=None) -> int:
        d = EVENT_DEFS[def_id]
        with self.db.tx():
            if d["kind"] == "contrib" and not location_id:
                raise GameError("Sự kiện này cần một địa điểm.")
            if d.get("spawn_ghost") and not ghost_instance_id:
                gid = wchoice(self.rng, LOCATIONS[location_id]["ghosts"])
                if gid:
                    ghost_instance_id = self.g.ghosts.spawn(gid, location_id)
            now = self.clock.now()
            title = d["title"] + (f" - {LOCATIONS[location_id]['name']}" if location_id else "")
            cur = self.db.run(
                "INSERT INTO world_events(def_id,kind,title,location_id,ghost_instance_id,progress,goal,started_at,ends_at) "
                "VALUES(?,?,?,?,?,0,?,?,?)",
                (def_id, d["kind"], title, location_id, ghost_instance_id, d.get("goal", 0), now,
                 now + (duration or d["duration"])))
            eid = cur.lastrowid
            if d["kind"] == "contrib" and location_id and not LOCATIONS[location_id].get("safe"):
                self.g.world.add_danger_mod(location_id, 1)
            self.announce("start", eid, title, d["desc"])
            return eid

    # ---- tham gia ------------------------------------------------------------------------
    def participate(self, uid, event_id, action_id) -> dict:
        act = CONTRIB_ACTIONS.get(action_id)
        if not act:
            raise GameError("Hành động không hợp lệ.")
        with self.db.tx():
            p = self.g.players.require_free(uid)
            ev = self.get(event_id)
            if ev["kind"] != "contrib" or ev["state"] != "active" or ev["ends_at"] <= self.clock.now():
                raise GameError("Sự kiện này không còn nhận đóng góp.")
            if p["location_id"] != ev["location_id"]:
                raise GameError(f"Bạn phải có mặt tại {LOCATIONS[ev['location_id']]['name']}.")
            self.g.players.check_cooldown(uid, f"ev{event_id}", 20)
            lines = []
            if action_id == "ap_che":
                lines += self._suppress_cost(uid)
            else:
                res = self.g.players.adjust(uid, hp=act.get("hp", 0), sanity=act.get("sanity", 0), rep=act.get("rep", 0))
                if res["died"]:
                    return {"lines": ["Bạn gục ngã tại hiện trường."], "done": False}
            # Đội hình: từ 3 người trở lên cùng tham gia thì mỗi hành động được +1 (đi lẻ là yếu thế)
            others = self.db.scalar("SELECT COUNT(*) FROM event_participants WHERE event_id=? AND user_id<>?",
                                    (event_id, uid), 0)
            contrib = act["contrib"] + (TEAM_BONUS if others + 1 >= TEAM_SIZE else 0)
            self.db.run("INSERT INTO event_participants(event_id,user_id,contribution) VALUES(?,?,?) "
                        "ON CONFLICT(event_id,user_id) DO UPDATE SET contribution=contribution+excluded.contribution",
                        (event_id, uid, contrib))
            self.db.run("UPDATE world_events SET progress=progress+? WHERE id=?", (contrib, event_id))
            self.bus.emit("event_joined", uid, event=ev["def_id"])
            ev = self.get(event_id)
            lines.append(f"+{contrib} đóng góp ({ev['progress']}/{ev['goal']})."
                         + (f" Đội hình {others + 1} người: +{TEAM_BONUS} yểm trợ." if contrib > act["contrib"] else ""))
            done = ev["progress"] >= ev["goal"]
            if done:
                lines += self.resolve_success(event_id)
            return {"lines": lines, "done": done}

    def _suppress_cost(self, uid) -> list[str]:
        owned = [g for g in self.g.ghosts.owned(uid) if g["resurrection"] + 12 < 100]
        if owned:
            g = min(owned, key=lambda x: x["resurrection"])
            self.db.run("UPDATE ghost_instances SET resurrection=resurrection+12 WHERE id=?", (g["id"],))
            self.g.players.adjust(uid, corruption=2)
            return [f"{GHOSTS[g['ghost_id']]['name']} gồng mình áp chế linh dị (+12 phục tô)."]
        if self.g.inv.count(uid, "bua_ap_che") > 0:
            self.g.inv.remove(uid, "bua_ap_che", 1)
            return ["Một lá Bùa Áp Chế cháy rụi trên hiện trường."]
        raise GameError("Bạn cần một lệ quỷ còn đủ sức hoặc một Bùa Áp Chế để áp chế.")

    # ---- kết thúc ---------------------------------------------------------------------------
    def resolve_success(self, event_id) -> list[str]:
        with self.db.tx():
            ev = self.get(event_id)
            d = EVENT_DEFS[ev["def_id"]]
            parts = self.participants(event_id)
            mult = d.get("reward_mult", 1.0)
            for r in parts:
                c = r["contribution"]
                apply_effects(self.g, r["user_id"], {"coins": int((20 + 5 * c) * mult), "exp": int((30 + 6 * c) * mult),
                                                      "rep": 2 + c // 4}, ev["title"])
                self.g.notify(r["user_id"], f"Sự kiện '{ev['title']}' đã được giải quyết. Phần thưởng đã gửi.")
            lines = ["Sự kiện được giải quyết!"]
            top = parts[0]["user_id"] if parts else None
            if top:
                apply_effects(self.g, top, {"items": {"vat_chua_vang": 1}}, "Đóng góp nhiều nhất")
                lines.append("Người đóng góp nhiều nhất nhận 1 Vật Chứa Vàng.")
                gi = ev["ghost_instance_id"]
                if gi:
                    inst = self.db.one("SELECT * FROM ghost_instances WHERE id=? AND state='free'", (gi,))
                    if inst:
                        self.db.run("UPDATE ghost_instances SET state='sealed',owner_id=?,location_id=NULL,"
                                    "resurrection=0 WHERE id=?", (top, gi))
                        self.bus.emit("ghost_sealed", top, ghost=inst["ghost_id"])
                        lines.append(f"{GHOSTS[inst['ghost_id']]['name']} bị phong ấn và giao cho người đóng góp nhiều nhất.")
            loc = ev["location_id"]
            if loc and not LOCATIONS[loc].get("safe"):
                self.g.world.add_danger_mod(loc, -1)
            self.g.world.add_unrest(-3)
            self.db.run("UPDATE world_events SET state='resolved' WHERE id=?", (event_id,))
            self.announce("success", event_id, ev["title"], "Sự kiện đã được các Ngự Quỷ Giả giải quyết.")
            return lines

    def resolve_fail(self, event_id):
        with self.db.tx():
            ev = self.get(event_id)
            d = EVENT_DEFS[ev["def_id"]]
            loc = ev["location_id"]
            safe = LOCATIONS[loc].get("safe") if loc else True
            if loc and not safe:
                self.g.world.lock(loc, d.get("fail_lock", 7200), f"Phong tỏa do {d['title']}")
                self.g.world.add_danger_mod(loc, 1)
            for r in self.participants(event_id):
                self.g.players.adjust(r["user_id"], hp=-(20 if safe else 10), reason=ev["title"])
                self.g.notify(r["user_id"], f"Sự kiện '{ev['title']}' thất bại. Bạn bị thương.")
            self.g.world.add_unrest(5)
            self.db.run("UPDATE world_events SET state='failed' WHERE id=?", (event_id,))
            where = f" {LOCATIONS[loc]['name']} bị phong tỏa." if loc and not safe else ""
            self.announce("fail", event_id, ev["title"], "Không ai kịp ngăn chặn linh dị." + where)

    def _expire(self, ev):
        d = EVENT_DEFS[ev["def_id"]]
        if ev["kind"] == "contrib":
            self.resolve_fail(ev["id"])
            return
        if ev["kind"] == "timed":
            pen = d.get("expire_penalty", {})
            u = d.get("unlocks")
            for r in self.db.all("SELECT user_id FROM players WHERE location_id=?", (u,)) if u else []:
                self.db.run("UPDATE players SET location_id=?,status='binh_thuong' WHERE user_id=?", (HUB, r["user_id"]))
                self.g.players.adjust(r["user_id"], sanity=pen.get("sanity", 0), corruption=pen.get("corruption", 0),
                                      reason="Bị đưa về khi tàu rời ga")
                self.g.notify(r["user_id"], "Chuyến tàu rời đi. Bạn bị đưa về Khu Trung Tâm trong tình trạng tồi tệ.")
        self.db.run("UPDATE world_events SET state='expired' WHERE id=?", (ev["id"],))
        self.announce("expire", ev["id"], ev["title"], "Sự kiện đã kết thúc.")

    # ---- nhịp thế giới ---------------------------------------------------------------------------
    def tick(self) -> list[dict]:
        with self.db.tx():
            now = self.clock.now()
            for ev in self.db.all("SELECT * FROM world_events WHERE state='active' AND ends_at<=?", (now,)):
                self._expire(ev)
            last = int(self.db.scalar("SELECT value FROM world_state WHERE key='last_decay'", default=0))
            if last == 0:
                self._set_state("last_decay", now)
            elif now - last >= DECAY_SECONDS:
                self.db.run("UPDATE location_state SET danger_mod=danger_mod-1 WHERE danger_mod>0")
                self._set_state("last_decay", now)
            self.g.econ._expire_trades()
            self.g.orgs.expire_missions()
            self._spawn_random()
        return self.drain_announcements()

    def _set_state(self, key, value):
        self.db.run("INSERT INTO world_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, str(value)))

    def _spawn_random(self):
        active = self.active()
        n_contrib = sum(1 for e in active if e["kind"] == "contrib")
        p = min(0.1, 0.012 + self.g.world.unrest() * 0.0008)
        if n_contrib < MAX_ACTIVE_CONTRIB and self.rng.random() < p:
            defs = {k: v["weight"] for k, v in EVENT_DEFS.items() if v["kind"] == "contrib" and v["weight"] > 0}
            locs = [lid for lid, loc in LOCATIONS.items()
                    if not loc.get("safe") and not loc.get("requires_event") and loc["ghosts"]
                    and not self.g.world.lock_info(lid)[0]
                    and not any(e["location_id"] == lid for e in active)]
            if locs:
                self.start_event(wchoice(self.rng, defs), self.rng.choice(locs))
        if not any(e["kind"] == "global" for e in active) and self.rng.random() < 0.01:
            defs = {k: v["weight"] for k, v in EVENT_DEFS.items() if v["kind"] == "global"}
            self.start_event(wchoice(self.rng, defs))
        if not any(e["kind"] == "timed" for e in active) and self.rng.random() < 0.008:
            defs = {k: v["weight"] for k, v in EVENT_DEFS.items() if v["kind"] == "timed"}
            self.start_event(wchoice(self.rng, defs))

    # ---- cốt truyện nhiều kết cục -----------------------------------------------------------------
    def start_story(self, uid, item_id) -> list[str]:
        story_id = STORY_BY_ITEM.get(item_id)
        if not story_id:
            raise GameError("Vật phẩm này không mở ra câu chuyện nào.")
        with self.db.tx():
            self.g.players.require_free(uid)
            if self.db.one("SELECT 1 FROM story_states WHERE user_id=?", (uid,)):
                raise GameError("Bạn đang đọc dở một câu chuyện. Hãy hoàn tất bằng /su_kien cau_chuyen.")
            self.g.inv.remove(uid, item_id, 1)
            story = STORIES[story_id]
            self.db.run("INSERT INTO story_states(user_id,story_id,node,started_at) VALUES(?,?,?,?)",
                        (uid, story_id, story["start"], self.clock.now()))
            return [f"**{story['title']}**", story["nodes"][story["start"]]["text"]]

    def story_view(self, uid) -> dict:
        st = self.db.one("SELECT * FROM story_states WHERE user_id=?", (uid,))
        if not st:
            raise GameError("Bạn chưa mở câu chuyện nào. Hãy đọc một Thư Linh Dị.")
        story = STORIES[st["story_id"]]
        node = story["nodes"][st["node"]]
        p = self.g.players.get(uid)
        choices = []
        for c in node["choices"]:
            ok, why = self._choice_ok(uid, p, c)
            choices.append({"id": c["id"], "label": c["label"], "ok": ok, "why": why})
        return {"title": story["title"], "text": node["text"], "choices": choices}

    def _choice_ok(self, uid, p, c):
        if c.get("req_loc") and p["location_id"] != c["req_loc"]:
            return False, f"Cần đang ở {LOCATIONS[c['req_loc']]['name']}"
        if c.get("req_item") and self.g.inv.count(uid, c["req_item"]) < 1:
            return False, "Thiếu vật phẩm"
        if c.get("req_org") and not self.g.orgs.member(uid):
            return False, "Cần là thành viên Tổng Bộ"
        return True, ""

    def story_choose(self, uid, choice_id) -> dict:
        with self.db.tx():
            st = self.db.one("SELECT * FROM story_states WHERE user_id=?", (uid,))
            if not st:
                raise GameError("Bạn chưa mở câu chuyện nào.")
            story = STORIES[st["story_id"]]
            node = story["nodes"][st["node"]]
            c = next((x for x in node["choices"] if x["id"] == choice_id), None)
            if not c:
                raise GameError("Lựa chọn không hợp lệ.")
            p = self.g.players.require_free(uid)
            ok, why = self._choice_ok(uid, p, c)
            if not ok:
                raise GameError(why + ".")
            if "goto" in c:
                self.db.run("UPDATE story_states SET node=? WHERE user_id=?", (c["goto"], uid))
                return {"ended": False, "text": story["nodes"][c["goto"]]["text"], "lines": []}
            end = story["endings"][c["end"]]
            for item, qty in end.get("consume", {}).items():
                self.g.inv.remove(uid, item, qty)
            self.db.run("DELETE FROM story_states WHERE user_id=?", (uid,))
            self.db.run("INSERT OR IGNORE INTO story_endings(user_id,story_id,ending_id,ts) VALUES(?,?,?,?)",
                        (uid, st["story_id"], c["end"], self.clock.now()))
            lines = apply_effects(self.g, uid, end["fx"], story["title"])
            self.g.players.log(uid, "story", f"{story['title']}: kết cục '{c['end']}'.")
            self.bus.emit("story_end", uid, story=st["story_id"], ending=c["end"])
            return {"ended": True, "text": end["text"], "lines": lines, "ending": c["end"]}

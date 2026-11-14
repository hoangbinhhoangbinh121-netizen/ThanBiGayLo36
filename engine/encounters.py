"""Đối mặt lệ quỷ (có lưu trạng thái trong DB, sống sót qua khởi động lại) và khám phá."""
from __future__ import annotations

import json

from core.errors import GameError
from core.util import wchoice
from data.basics import ITEMS
from data.ghosts import GHOSTS, RANK_LEVEL
from data.locations import LOCATIONS
from engine.economy import apply_effects
from engine.mechanics import MECHANICS
from engine.players import Service


def _half(dmg: dict) -> dict:
    return {k: (int(v / 2) if v < 0 else v) for k, v in dmg.items()}


class EncounterService(Service):
    # ---- nạp / lưu ------------------------------------------------------------
    def active(self, uid):
        return self.db.one("SELECT * FROM encounters WHERE user_id=?", (uid,))

    def _load(self, uid):
        enc = self.active(uid)
        if not enc:
            raise GameError("Bạn không ở trong cuộc đối mặt nào.")
        return enc, json.loads(enc["state_json"])

    def _save(self, uid, st):
        self.db.run("UPDATE encounters SET state_json=? WHERE user_id=?", (json.dumps(st), uid))

    def _known(self, uid, ghost_id, st):
        return set(range(len(GHOSTS[ghost_id]["clues"]))) if st.get("reveal") else self.g.ghosts.clues_known(uid, ghost_id)

    def _end(self, uid):
        self.db.run("DELETE FROM encounters WHERE user_id=?", (uid,))

    # ---- bắt đầu ---------------------------------------------------------------------
    def start(self, uid, ghost_id) -> dict:
        with self.db.tx():
            p = self.g.players.require_free(uid)
            loc = p["location_id"]
            gd = GHOSTS[ghost_id]
            inst_id = self.g.ghosts.free_instance(loc, ghost_id)
            mech = MECHANICS[gd["mechanic"]]
            st = mech.start(self.rng)
            st.update(phase="fight", bind_bonus=0.0, reveal=0, domain=1 if self.g.players.buff(uid, "domain") else 0)
            shield = self.g.players.use_buff(uid, "shadow")
            if shield:
                st["shield"] = st.get("shield", 0) + shield
            entry = dict(gd["domain"]["entry"])
            if st["domain"]:
                entry = _half(entry)
            self.g.ghosts.mark_seen(uid, ghost_id)
            res = self.g.players.adjust(uid, sanity=entry.get("sanity", 0), corruption=entry.get("corruption", 0),
                                        reason=f"Quỷ vực {gd['domain']['name']}")
            if res["died"] or res["breakdown"]:
                return {"started": False, "res": res}
            self.db.run("INSERT INTO encounters(user_id,ghost_instance_id,ghost_id,location_id,state_json,created_at) "
                        "VALUES(?,?,?,?,?,?)", (uid, inst_id, ghost_id, loc, json.dumps(st), self.clock.now()))
            self.bus.emit("encounter_started", uid, ghost=ghost_id)
            return {"started": True, "ghost_id": ghost_id, "domain": gd["domain"], "entry": entry}

    # ---- hiển thị ----------------------------------------------------------------------
    def view(self, uid) -> dict:
        enc, st = self._load(uid)
        gd = GHOSTS[enc["ghost_id"]]
        known = self._known(uid, enc["ghost_id"], st)
        out = {"ghost_id": enc["ghost_id"], "ghost": gd, "phase": st["phase"], "shield": st.get("shield", 0),
               "hints": [gd["clues"][i] for i in sorted(known)], "inst_id": enc["ghost_instance_id"]}
        if st["phase"] == "fight":
            inv = self.g.inv
            scene = MECHANICS[gd["mechanic"]].scene(st, known, lambda i: inv.count(uid, i) > 0)
            out["scene"] = scene
            out["powers"] = [(g, pw) for g in self.g.ghosts.owned(uid) for pw in GHOSTS[g["ghost_id"]]["powers"]
                             if pw["enc"]]
        else:
            inst = self.g.ghosts.get(enc["ghost_instance_id"])
            out["bind_chance"] = self.g.ghosts.bind_chance(uid, inst, st["bind_bonus"])
            out["has_container"] = self.g.inv.count(uid, "vat_chua_vang") > 0
            held = {o["ghost_id"] for o in self.g.ghosts.owned(uid)}
            out["already_held"] = enc["ghost_id"] in held
        return out

    # ---- hành động ------------------------------------------------------------------------
    def act(self, uid, opt_id) -> dict:
        with self.db.tx():
            p = self.g.players.refresh(uid)
            enc, st = self._load(uid)
            if st["phase"] != "fight":
                raise GameError("Cuộc đối mặt đã lắng xuống. Hãy chọn khống chế, phong ấn hoặc rời đi.")
            gd = GHOSTS[enc["ghost_id"]]
            mech = MECHANICS[gd["mechanic"]]
            inv = self.g.inv
            known = self._known(uid, enc["ghost_id"], st)
            scene = mech.scene(st, known, lambda i: inv.count(uid, i) > 0)
            opt = next((o for o in scene.options if o.id == opt_id), None)
            if not opt:
                raise GameError("Lựa chọn này không còn khả dụng.")
            if opt.item:
                inv.remove(uid, opt.item, 1)
            step = mech.act(st, opt_id, self.rng, p)
            lines = [step.text]
            dmg = _half(step.dmg) if st.get("domain") else step.dmg
            res = self.g.players.adjust(uid, hp=dmg.get("hp", 0), sanity=dmg.get("sanity", 0),
                                        corruption=dmg.get("corruption", 0), reason=f"{gd['name']} ({step.text[:30]})")
            if step.fx:
                lines += apply_effects(self.g, uid, step.fx, gd["name"])
            st["bind_bonus"] = st.get("bind_bonus", 0.0) + step.bind_bonus
            for k, label in (("hp", "thể chất"), ("sanity", "tinh thần")):
                if dmg.get(k):
                    lines.append(f"{dmg[k]} {label}")
            if step.outcome == "continue" and not (res["died"] or res["saved"] or res["breakdown"]):
                # Linh dị dao động: quỷ đã biết vẫn gây áp lực lên tinh thần (tăng theo nguy hiểm khu vực và hạng quỷ)
                danger = self.g.world.effective_danger(enc["location_id"])
                if self.rng.random() < min(0.45, 0.15 + 0.03 * danger):
                    noise = -(1 + RANK_LEVEL[gd["rank"]])
                    noise = int(noise / 2) if st.get("domain") else noise
                    nres = self.g.players.adjust(uid, sanity=noise, reason=f"Linh dị dao động quanh {gd['name']}")
                    lines.append(f"Linh dị dao động quanh bạn: {noise} tinh thần.")
                    res["breakdown"] = res["breakdown"] or nres["breakdown"]
            if step.outcome == "death" and not (res["died"] or res["saved"]):
                res = {**res, **self.g.players.die(uid, f"{gd['name']}: vi phạm quy luật")}
            if res["died"]:
                return {"status": "death", "lines": lines + ["Bạn đã chết. Hồi sinh ở Khu Trung Tâm với tổn thất."]}
            if res["saved"]:
                return {"status": "saved", "lines": lines + ["Hình Nhân Thế Mạng vỡ vụn; lệ quỷ mất hứng bỏ đi."]}
            if res["breakdown"]:
                return {"status": "breakdown", "lines": lines + ["Tinh thần sụp đổ giữa cuộc đối mặt!"]}
            if step.outcome == "survive":
                st["phase"] = "cleared"
                self._save(uid, st)
                danger = self.g.world.effective_danger(enc["location_id"])
                rl = RANK_LEVEL[gd["rank"]]
                coins = 8 * rl + 3 * danger          # đối mặt là cách kiếm tiền rủi ro cao nhất
                self.g.players.adjust(uid, exp=15 * rl + 5 * danger, rep=1 if rl >= 2 else 0, coins=coins)
                self.g.players.log(uid, "survive", f"Sống sót trước {gd['name']}.")
                self.bus.emit("encounter_survived", uid, ghost=enc["ghost_id"])
                return {"status": "cleared", "lines": lines + [f"Bạn sống sót! +{15 * rl + 5 * danger} kinh nghiệm, +{coins} tiền cổ."]}
            self._save(uid, st)
            return {"status": "continue", "lines": lines}

    def use_power(self, uid, inst_id, power_id) -> dict:
        with self.db.tx():
            self.g.players.refresh(uid)
            enc, st = self._load(uid)
            if st["phase"] != "fight":
                raise GameError("Cuộc đối mặt đã lắng xuống.")
            inst = self.g.ghosts.get_owned(uid, inst_id)
            pw = self.g.ghosts.find_power(inst, power_id)
            if not pw["enc"]:
                raise GameError("Năng lực này không dùng được trong đối mặt.")
            paid = self.g.ghosts.pay_power(uid, inst, pw)
            name = GHOSTS[inst["ghost_id"]]["name"]
            if paid["resurrected"]:
                return {"status": "resurrected", "lines": [f"{name} phục tô giữa cuộc đối mặt!"]}
            kind, strong = pw["enc"], bool(inst["awakened"])
            lines = [f"{pw['name']} ({name}): phục tô +{paid['cost']:.0f}% → {paid['new']:.0f}%."]
            mech = MECHANICS[GHOSTS[enc["ghost_id"]]["mechanic"]]
            if kind == "escape":
                self._end(uid)
                return {"status": "escaped", "lines": lines + ["Cánh cửa mở ra: bạn thoát khỏi cuộc đối mặt."]}
            if kind == "progress":
                mech.boost(st)
                lines.append("Bạn tiến thêm một nhịp.")
            if kind in ("shield", "shield_reveal"):
                st["shield"] = st.get("shield", 0) + (2 if strong else 1)
                lines.append("Khiên bóng chặn đòn kế tiếp.")
            if kind in ("reveal", "shield_reveal"):
                st["reveal"] = 1
                lines.append("Mọi quy luật đã biết hiện ra trước mắt.")
            self._save(uid, st)
            return {"status": "continue", "lines": lines}

    def flee(self, uid) -> dict:
        with self.db.tx():
            p = self.g.players.refresh(uid)
            enc, st = self._load(uid)
            gd = GHOSTS[enc["ghost_id"]]
            if st["phase"] != "fight":
                raise GameError("Hãy chọn rời đi thay vì bỏ chạy.")
            if not MECHANICS[gd["mechanic"]].can_flee:
                res = self.g.players.adjust(uid, sanity=-8, reason="Không lối thoát khỏi quỷ vực")
                return {"status": "died" if res["died"] else "continue", "lines": ["Không có lối ra. Mọi hướng đều quay về chỗ cũ."]}
            chance = max(0.15, 0.45 + 0.2 * p["sanity"] / p["max_sanity"] - 0.04 * RANK_LEVEL[gd["rank"]])
            if self.rng.random() < chance:
                self._end(uid)
                self.g.players.adjust(uid, sanity=-4)
                return {"status": "escaped", "lines": ["Bạn chạy thoát, tim đập loạn. Lệ quỷ ở lại nơi này."]}
            res = self.g.players.adjust(uid, hp=-10, sanity=-6, reason=f"Bỏ chạy khỏi {gd['name']} thất bại")
            if res["died"]:
                return {"status": "death", "lines": ["Bạn bị tóm lại khi đang chạy. Bạn đã chết."]}
            return {"status": "continue", "lines": ["Bạn vấp ngã, lệ quỷ chặn đường. -10 thể chất, -6 tinh thần."]}

    # ---- sau khi sống sót ---------------------------------------------------------------------
    def _need_cleared(self, uid):
        enc, st = self._load(uid)
        if st["phase"] != "cleared":
            raise GameError("Lệ quỷ vẫn đang tấn công, chưa thể làm điều này.")
        return enc, st

    def bind(self, uid) -> dict:
        with self.db.tx():
            enc, st = self._need_cleared(uid)
            res = self.g.ghosts.bind(uid, enc["ghost_instance_id"], st.get("bind_bonus", 0.0))
            self._end(uid)
            return res

    def seal(self, uid) -> dict:
        with self.db.tx():
            enc, st = self._need_cleared(uid)
            res = self.g.ghosts.seal(uid, enc["ghost_instance_id"])
            self._end(uid)
            return res

    def leave(self, uid):
        with self.db.tx():
            self._need_cleared(uid)
            self._end(uid)
            self.g.players.log(uid, "leave", "Rời khỏi lệ quỷ đã lắng xuống, để nó lại nơi cũ.")


# =============================================================== Khám phá
MODES = {
    "tham_do": {"name": "Thăm dò", "sanity": 3, "cd": 15,
                "w": {"nothing": 30, "loot": 30, "clue": 15, "incident": 12, "encounter": 13}},
    "dieu_tra": {"name": "Điều tra manh mối", "sanity": 6, "cd": 20,
                 "w": {"nothing": 18, "loot": 8, "clue": 46, "incident": 10, "encounter": 18}},
    "tim_do": {"name": "Tìm vật phẩm", "sanity": 4, "cd": 15,
               "w": {"nothing": 22, "loot": 56, "clue": 4, "incident": 10, "encounter": 8}},
}
NOTHING = ["Bạn lục soát cẩn thận nhưng chỉ thấy bụi và im lặng.",
           "Không có gì ở đây, hoặc có gì đó nhưng nó không muốn bị tìm thấy.",
           "Bạn đi hết một vòng. Chỉ có tiếng bước chân bạn, và đôi khi, tiếng bước chân khác."]


class ExplorationService(Service):
    def explore(self, uid, mode) -> dict:
        m = MODES.get(mode)
        if not m:
            raise GameError("Hình thức khám phá không hợp lệ.")
        with self.db.tx():
            p = self.g.players.require_free(uid)
            lid = p["location_id"]
            loc = LOCATIONS[lid]
            if loc.get("safe"):
                raise GameError("Nơi này an toàn, không có gì để khám phá. Hãy di chuyển tới khu vực linh dị.")
            locked, reason, left = self.g.world.lock_info(lid)
            if locked:
                raise GameError(f"{loc['name']} đang bị phong tỏa ({reason}).")
            danger = self.g.world.effective_danger(lid)
            cost = m["sanity"] + danger // 2
            if p["sanity"] <= cost:
                raise GameError(f"Tinh thần quá yếu ({p['sanity']}), cần hơn {cost}. Hãy nghỉ ngơi.")
            self.g.players.check_cooldown(uid, "explore", m["cd"])
            mods = self.g.world.modifiers()
            pl = self.g.players
            domain = pl.use_buff(uid, "domain")
            w = dict(m["w"])
            w["encounter"] += danger * 2 + mods["encounter_add"] + (10 if p["corruption"] >= 40 else 0)
            if domain:
                danger = max(1, danger - 3)
                w["encounter"] //= 2
            w["clue"] += int(mods["clue_bonus"] * 100)
            kind = wchoice(self.rng, w)
            if mode == "dieu_tra" and pl.buff(uid, "sight"):
                pl.use_buff(uid, "sight")
                kind = "clue"
            pl.adjust(uid, sanity=-cost)
            self.g.world._row(lid)
            self.db.run("UPDATE location_state SET explored=explored+1 WHERE location_id=?", (lid,))
            self.bus.emit("explored", uid, loc=lid)
            res = {"kind": kind, "cost": cost, "lines": [], "encounter": False, "mode": m["name"], "loc": lid}
            if kind == "clue" and not self._clue(uid, loc, res):
                kind = res["kind"] = "loot"
            if kind == "loot":
                self._loot(uid, loc, mods, res)
            elif kind == "incident":
                self._incident(uid, loc, res)
            elif kind == "encounter":
                self._encounter(uid, loc, res)
            elif kind == "nothing":
                res["lines"].append(self.rng.choice(NOTHING))
            return res

    def _clue(self, uid, loc, res) -> bool:
        cand = {}
        for gid, wt in loc["ghosts"].items():
            if self.g.ghosts.unknown_clue(uid, gid) is not None:
                cand[gid] = wt
        gid = wchoice(self.rng, cand)
        if not gid:
            return False
        idx = self.g.ghosts.unknown_clue(uid, gid)
        self.g.ghosts.add_clue(uid, gid, idx)
        res["kind"] = "clue"
        res["clue"] = (gid, idx)
        res["lines"] += [f"Bạn tìm ra manh mối về **{GHOSTS[gid]['name']}**:", GHOSTS[gid]["clues"][idx]]
        return True

    def _loot(self, uid, loc, mods, res):
        fx = {"items": {}, "coins": 0}
        rolls = 1 + (1 if self.g.players.use_buff(uid, "loot") else 0)
        if self.rng.random() < mods["loot_mult"] - 1:
            rolls += 1
        for _ in range(rolls):
            item = wchoice(self.rng, loc["loot"])
            if item and self.rng.random() < 0.6:
                fx["items"][item] = fx["items"].get(item, 0) + 1
            else:
                lo, hi = loc["coins"]
                fx["coins"] += self.rng.randint(lo, hi)
        if not fx["items"]:
            fx.pop("items")
        if not fx["coins"]:
            fx.pop("coins")
        res["lines"].append("Bạn lục được thứ gì đó còn dùng được.")
        res["lines"] += apply_effects(self.g, uid, fx, "Tìm đồ")

    def _incident(self, uid, loc, res):
        if not loc["incidents"]:
            res["lines"].append(self.rng.choice(NOTHING))
            return
        table = {i: inc[0] for i, inc in enumerate(loc["incidents"])}
        _, text, fx = loc["incidents"][wchoice(self.rng, table)]
        res["lines"].append(text)
        res["lines"] += apply_effects(self.g, uid, fx, "Sự cố khi khám phá")

    def _encounter(self, uid, loc, res):
        gid = wchoice(self.rng, loc["ghosts"])
        if not gid:
            return self._incident(uid, loc, res)
        info = self.g.enc.start(uid, gid)
        res["ghost"] = gid
        if not info["started"]:
            res["lines"].append("Quỷ vực ập xuống quá nhanh; bạn gục ngã trước khi kịp phản ứng.")
            return
        gd = GHOSTS[gid]
        res["encounter"] = True
        res["lines"].append(f"**{gd['name']}** xuất hiện. Bạn bước vào quỷ vực **{info['domain']['name']}**: "
                            f"{info['domain']['desc']}")
        if info["entry"].get("sanity"):
            res["lines"].append(f"{info['entry']['sanity']} tinh thần")

"""Hệ thống Ngự Quỷ Giả: khống chế, phục tô, cân bằng linh dị, khắc chế, thức tỉnh, phong ấn."""
from __future__ import annotations

from core.errors import GameError
from core.util import clamp
from data.ghosts import BIND_BASE, GHOSTS, RANK_LEVEL, suppressors_of
from data.locations import HUB
from engine.players import LOSS_SECONDS, Service


class GhostService(Service):
    # ---- truy vấn ------------------------------------------------------------
    def get(self, inst_id):
        r = self.db.one("SELECT * FROM ghost_instances WHERE id=?", (inst_id,))
        if not r:
            raise GameError("Lệ quỷ này không còn tồn tại.")
        return r

    def owned(self, uid):
        return self.db.all("SELECT * FROM ghost_instances WHERE owner_id=? AND state='bound' ORDER BY id", (uid,))

    def sealed_by(self, uid):
        return self.db.all("SELECT * FROM ghost_instances WHERE owner_id=? AND state='sealed' ORDER BY id", (uid,))

    def get_owned(self, uid, inst_id):
        r = self.db.one("SELECT * FROM ghost_instances WHERE id=? AND owner_id=? AND state='bound'", (inst_id, uid))
        if not r:
            raise GameError("Bạn không giữ lệ quỷ này.")
        return r

    def spawn(self, ghost_id, loc) -> int:
        if ghost_id not in GHOSTS:
            raise GameError("Lệ quỷ không tồn tại.")
        now = self.clock.now()
        cur = self.db.run("INSERT INTO ghost_instances(ghost_id,state,location_id,updated_at,created_at) "
                          "VALUES(?, 'free', ?, ?, ?)", (ghost_id, loc, now, now))
        return cur.lastrowid

    def free_instance(self, loc, ghost_id) -> int:
        r = self.db.one("SELECT id FROM ghost_instances WHERE state='free' AND location_id=? AND ghost_id=? "
                        "ORDER BY id LIMIT 1", (loc, ghost_id))
        return r["id"] if r else self.spawn(ghost_id, loc)

    # ---- khe chứa & cân bằng ---------------------------------------------------
    def max_slots(self, p) -> int:
        return min(4, 1 + p["level"] // 12)

    def balance(self, uid) -> int:
        return sum(GHOSTS[g["ghost_id"]]["polarity"] for g in self.owned(uid))

    def rate_for(self, inst, owned, p) -> float:
        """Tốc độ phục tô mỗi giờ: phụ thuộc quá tải khe, mất cân bằng, khắc chế, xung đột, quỷ vực, nhiễm linh dị."""
        gd = GHOSTS[inst["ghost_id"]]
        m = 1.0
        n, slots = len(owned), self.max_slots(p)
        if n > slots:
            m *= 1 + 0.5 * (n - slots)
        if abs(sum(GHOSTS[o["ghost_id"]]["polarity"] for o in owned)) >= 3:
            m *= 1.5
        for o in owned:
            if o["id"] == inst["id"]:
                continue
            og = GHOSTS[o["ghost_id"]]
            if inst["ghost_id"] in og["suppresses"]:
                m *= 0.5
            if o["ghost_id"] in gd["conflicts"] or inst["ghost_id"] in og["conflicts"]:
                m *= 1.4
            if o["ghost_id"] == "quy_vuc" and inst["ghost_id"] != "quy_vuc":
                m *= 1.3
        if p["corruption"] >= 40:
            m *= 1.25
        if inst["awakened"]:
            m *= 0.8
        return gd["rate"] * m

    # ---- phục tô -----------------------------------------------------------------
    def tick_owner(self, uid):
        owned = self.owned(uid)
        if not owned:
            return
        p = self.db.one("SELECT level,corruption FROM players WHERE user_id=?", (uid,))
        now = self.clock.now()
        for inst in owned:
            hours = max(0.0, (now - inst["updated_at"]) / 3600)
            new = inst["resurrection"] + self.rate_for(inst, owned, p) * hours
            self.db.run("UPDATE ghost_instances SET resurrection=?,updated_at=? WHERE id=?", (new, now, inst["id"]))
        self.check_resurrections(uid)

    def check_resurrections(self, uid):
        for inst in self.owned(uid):
            if inst["resurrection"] >= 100:
                self.resurrect(inst["id"])

    def reduce_resurrection(self, inst_id, amount) -> float:
        inst = self.get(inst_id)
        new = max(0.0, inst["resurrection"] - amount)
        self.db.run("UPDATE ghost_instances SET resurrection=? WHERE id=?", (new, inst_id))
        return new

    def resurrect(self, inst_id) -> str:
        with self.db.tx():
            inst = self.get(inst_id)
            uid = inst["owner_id"]
            gd = GHOSTS[inst["ghost_id"]]
            p = self.g.players.get(uid)
            loc, now = p["location_id"], self.clock.now()
            self.db.run("UPDATE ghost_instances SET state='free',owner_id=NULL,location_id=?,resurrection=0,"
                        "updated_at=? WHERE id=?", (loc, now, inst_id))
            self.db.run(
                "UPDATE players SET status='mat_kiem_soat',status_until=?,hp=MAX(1,hp-max_hp*30/100),"
                "sanity=MAX(1,MIN(sanity,max_sanity/5)),corruption=MIN(100,corruption+15) WHERE user_id=?",
                (now + LOSS_SECONDS, uid))
            self.db.run("DELETE FROM encounters WHERE user_id=?", (uid,))
            self.g.players.log(uid, "resurrect", f"{gd['name']} phục tô! {gd['resurrect_text']}")
            self.g.world.add_unrest(5)
            self.bus.emit("resurrected", uid, ghost=inst["ghost_id"])
            self.bus.emit("lost_control", uid, why="lệ quỷ phục tô")
            self.g.events.start_event("phuc_to", loc, ghost_instance_id=inst_id)
            self.g.notify(uid, f"{gd['name']} phục tô! Bạn mất kiểm soát.")
            return gd["resurrect_text"]

    # ---- manh mối & bách khoa ---------------------------------------------------------
    def mark_seen(self, uid, ghost_id):
        self.db.run("INSERT OR IGNORE INTO stats(user_id,key,value) VALUES(?,?,1)", (uid, f"seen:{ghost_id}"))

    def seen(self, uid, ghost_id) -> bool:
        return self.db.one("SELECT 1 FROM stats WHERE user_id=? AND key=?", (uid, f"seen:{ghost_id}")) is not None

    def clues_known(self, uid, ghost_id) -> set:
        return {r["clue_idx"] for r in
                self.db.all("SELECT clue_idx FROM player_clues WHERE user_id=? AND ghost_id=?", (uid, ghost_id))}

    def unknown_clue(self, uid, ghost_id):
        known = self.clues_known(uid, ghost_id)
        return next((i for i in range(len(GHOSTS[ghost_id]["clues"])) if i not in known), None)

    def add_clue(self, uid, ghost_id, idx) -> bool:
        cur = self.db.run("INSERT OR IGNORE INTO player_clues(user_id,ghost_id,clue_idx,found_at) VALUES(?,?,?,?)",
                          (uid, ghost_id, idx, self.clock.now()))
        if cur.rowcount:
            self.g.players.log(uid, "clue", f"Tìm được manh mối về {GHOSTS[ghost_id]['name']}.")
            self.bus.emit("clue_found", uid, ghost=ghost_id, idx=idx)
            return True
        return False

    def codex(self, uid, ghost_id) -> dict:
        """Bách khoa lệ quỷ: lộ thông tin theo mức hiểu biết (đã gặp + số manh mối)."""
        gd = GHOSTS[ghost_id]
        seen, known = self.seen(uid, ghost_id), self.clues_known(uid, ghost_id)
        f = {"name": gd["name"] if seen or known else "???"}
        if seen or known:
            f.update(origin=gd["origin"], rank=gd["rank"], range=gd["range"], domain=gd["domain"],
                     polarity=gd["polarity"])
        if 0 in known:
            f["kill_rule"] = gd["kill_rule"]
        if 1 in known:
            f["counter"] = gd["counter"]
        if 2 in known:
            f["suppress"] = gd["suppress_text"]
        if len(known) == len(gd["clues"]):
            f["awaken"] = gd["awaken"]
            f["relations"] = {"suppresses": gd["suppresses"], "conflicts": gd["conflicts"]}
        return {"seen": seen, "clues": known, "fields": f, "ghost": gd}

    # ---- năng lực -------------------------------------------------------------------------
    def find_power(self, inst, power_id):
        for pw in GHOSTS[inst["ghost_id"]]["powers"]:
            if pw["id"] == power_id:
                return pw
        raise GameError("Lệ quỷ này không có năng lực đó.")

    def pay_power(self, uid, inst, power) -> dict:
        """Trả giá phục tô + nhiễm linh dị. Dùng khi ổn định (phục tô < 60) sẽ tích lũy thức tỉnh."""
        awakened = bool(inst["awakened"])
        cost = power["cost"] * (0.7 if awakened else 1.0)
        before = inst["resurrection"]
        new = before + cost
        stable = inst["stable_uses"] + (1 if before < 60 else 0)
        awaken_now = (not awakened) and stable >= 6
        self.db.run("UPDATE ghost_instances SET resurrection=?,uses=uses+1,stable_uses=?,awakened=? WHERE id=?",
                    (new, stable, 1 if (awakened or awaken_now) else 0, inst["id"]))
        out = {"cost": cost, "new": new, "awakened_now": awaken_now, "resurrected": False}
        if awaken_now:
            self.g.players.log(uid, "awaken", f"{GHOSTS[inst['ghost_id']]['name']} thức tỉnh!")
            self.bus.emit("awakened", uid, ghost=inst["ghost_id"])
            self.g.notify(uid, GHOSTS[inst["ghost_id"]]["awaken"])
        if new >= 100:
            self.resurrect(inst["id"])
            out["resurrected"] = True
        else:
            self.g.players.adjust(uid, corruption=power["corr"])
        return out

    def use_power(self, uid, inst_id, power_id, target_inst_id=None) -> list[str]:
        with self.db.tx():
            p = self.g.players.require_free(uid)
            inst = self.get_owned(uid, inst_id)
            pw = self.find_power(inst, power_id)
            out, strong = pw["out"], bool(inst["awakened"])
            target = None
            if out == "suppress":
                target = self.get_owned(uid, target_inst_id) if target_inst_id else None
                if not target or target["id"] == inst["id"]:
                    raise GameError("Hãy chọn một lệ quỷ KHÁC mà bạn đang giữ để áp chế.")
            if out == "teleport" and p["location_id"] == HUB:
                raise GameError("Bạn đã ở nơi an toàn rồi.")
            paid = self.pay_power(uid, inst, pw)
            name = GHOSTS[inst["ghost_id"]]["name"]
            if paid["resurrected"]:
                return [f"{name} phục tô ngay khi bạn gọi nó! {GHOSTS[inst['ghost_id']]['resurrect_text']}"]
            lines = [f"Dùng {pw['name']} ({name}): phục tô +{paid['cost']:.0f}% → {paid['new']:.0f}%."]
            pl = self.g.players
            if out == "loot":
                pl.set_buff(uid, "loot", 4 if strong else 2)
                lines.append(f"{4 if strong else 2} lần Tìm đồ kế tiếp được thêm một lượt nhặt.")
            elif out == "shadow":
                pl.set_buff(uid, "shadow", 2 if strong else 1)
                lines.append("Lần đối mặt kế tiếp bạn có khiên bóng.")
            elif out == "sight":
                pl.set_buff(uid, "sight", 2 if strong else 1)
                lines.append("Lần Điều tra manh mối kế tiếp chắc chắn ra manh mối.")
            elif out == "suppress":
                new = self.reduce_resurrection(target["id"], 60 if strong else 35)
                lines.append(f"{GHOSTS[target['ghost_id']]['name']} bị áp chế, phục tô còn {new:.0f}%.")
            elif out == "teleport":
                self.db.run("UPDATE players SET location_id=? WHERE user_id=?", (HUB, uid))
                lines.append("Cánh cửa mở ra: bạn đã về Khu Trung Tâm.")
            elif out == "domain":
                pl.set_buff(uid, "domain", 5 if strong else 3)
                lines.append(f"Quỷ vực che phủ: {5 if strong else 3} lần Khám phá kế tiếp ít nguy hiểm hơn.")
            return lines

    # ---- khống chế / phong ấn / bàn giao ----------------------------------------------------
    def bind_chance(self, uid, inst, bonus=0.0) -> float:
        p = self.g.players.get(uid)
        gd = GHOSTS[inst["ghost_id"]]
        chance = BIND_BASE[gd["rank"]]
        chance += 0.10 * min(3, len(self.clues_known(uid, inst["ghost_id"])))
        held = {o["ghost_id"] for o in self.owned(uid)}
        if held & set(suppressors_of(inst["ghost_id"])):
            chance += 0.25
        chance *= 0.6 + 0.4 * (p["sanity"] / p["max_sanity"])
        chance -= 0.002 * p["corruption"]
        return clamp(chance + bonus, 0.05, 0.95)

    def bind(self, uid, inst_id, bonus=0.0) -> dict:
        with self.db.tx():
            p = self.g.players.get(uid)
            inst = self.get(inst_id)
            if inst["state"] != "free" or inst["location_id"] != p["location_id"]:
                raise GameError("Lệ quỷ này không còn ở đây để khống chế.")
            owned = self.owned(uid)
            if any(o["ghost_id"] == inst["ghost_id"] for o in owned):
                raise GameError("Hai thực thể cùng quy luật không thể cùng ở trong một cơ thể.")
            chance = self.bind_chance(uid, inst, bonus)
            gd = GHOSTS[inst["ghost_id"]]
            if self.rng.random() < chance:
                over = len(owned) >= self.max_slots(p)
                first = not p["is_summoner"]
                self.db.run("UPDATE ghost_instances SET state='bound',owner_id=?,location_id=NULL,resurrection=10,"
                            "updated_at=? WHERE id=?", (uid, self.clock.now(), inst_id))
                self.db.run("UPDATE players SET is_summoner=1 WHERE user_id=?", (uid,))
                if over:
                    self.g.players.adjust(uid, corruption=10)
                self.g.players.log(uid, "bind", f"Khống chế {gd['name']}.")
                self.bus.emit("bound", uid, ghost=inst["ghost_id"])
                return {"success": True, "chance": chance, "over": over, "first": first, "ghost": inst["ghost_id"]}
            res = self.g.players.adjust(uid, sanity=-20, corruption=8, hp=-10, reason=f"Khống chế {gd['name']} thất bại")
            self.g.players.log(uid, "bind_fail", f"Khống chế {gd['name']} thất bại.")
            return {"success": False, "chance": chance, "ghost": inst["ghost_id"], "died": res["died"]}

    def seal(self, uid, inst_id) -> dict:
        with self.db.tx():
            p = self.g.players.get(uid)
            inst = self.get(inst_id)
            gd = GHOSTS[inst["ghost_id"]]
            if inst["state"] == "free":
                if inst["location_id"] != p["location_id"]:
                    raise GameError("Lệ quỷ này không ở đây.")
            elif not (inst["state"] == "bound" and inst["owner_id"] == uid):
                raise GameError("Bạn không thể phong ấn lệ quỷ này.")
            self.g.inv.remove(uid, "vat_chua_vang", 1)
            self.db.run("UPDATE ghost_instances SET state='sealed',owner_id=?,location_id=NULL,resurrection=0 "
                        "WHERE id=?", (uid, inst_id))
            rl = RANK_LEVEL[gd["rank"]]
            self.g.players.adjust(uid, exp=40 * rl, rep=2 * rl, coins=30 * rl)
            self.g.players.log(uid, "seal", f"Phong ấn {gd['name']} trong Vật Chứa Vàng.")
            self.bus.emit("ghost_sealed", uid, ghost=inst["ghost_id"])
            return {"ghost": inst["ghost_id"], "exp": 40 * rl, "rep": 2 * rl, "coins": 30 * rl}

    def hand_over(self, uid, inst_id) -> dict:
        with self.db.tx():
            inst = self.db.one("SELECT * FROM ghost_instances WHERE id=? AND owner_id=? AND state='sealed'",
                               (inst_id, uid))
            if not inst:
                raise GameError("Bạn không có Vật Chứa Vàng này.")
            if not self.g.orgs.member(uid):
                raise GameError("Chỉ thành viên Tổng Bộ mới bàn giao được cho kho lưu giữ.")
            rl = RANK_LEVEL[GHOSTS[inst["ghost_id"]]["rank"]]
            self.db.run("DELETE FROM ghost_instances WHERE id=?", (inst_id,))
            self.g.orgs.add_treasury(40 * rl)
            self.g.players.adjust(uid, coins=150 * rl, rep=8 * rl)
            self.g.orgs.add_contribution(uid, 10 * rl)
            self.g.orgs.archive_add(inst["ghost_id"], uid)
            self.g.players.log(uid, "handover", f"Bàn giao {GHOSTS[inst['ghost_id']]['name']} cho kho Tổng Bộ.")
            self.bus.emit("handed_over", uid, ghost=inst["ghost_id"])
            return {"ghost": inst["ghost_id"], "coins": 150 * rl, "rep": 8 * rl}

    def rescue(self, actor, target) -> dict:
        """Đồng đội dùng Bùa Áp Chế kéo người đang mất kiểm soát ra (cùng địa điểm)."""
        if actor == target:
            raise GameError("Bạn không thể tự cứu mình bằng cách này.")
        with self.db.tx():
            a = self.g.players.require_free(actor)
            t = self.g.players.refresh(target)
            if t["status"] != "mat_kiem_soat":
                raise GameError("Người này không đang mất kiểm soát.")
            if a["location_id"] != t["location_id"]:
                raise GameError("Bạn phải ở cùng địa điểm với người cần cứu.")
            self.g.inv.remove(actor, "bua_ap_che", 1)
            self.g.players.end_lost_control(target)
            for gh in self.owned(target):
                self.reduce_resurrection(gh["id"], 30)
            self.g.players.adjust(actor, rep=2, exp=20)
            self.g.players.log(actor, "rescue", "Dùng Bùa Áp Chế cứu một đồng đội mất kiểm soát.")
            self.g.players.log(target, "rescue", "Được đồng đội dùng Bùa Áp Chế kéo ra khỏi mất kiểm soát.")
            self.g.notify(target, "Một đồng đội đã dán Bùa Áp Chế và kéo bạn ra khỏi mất kiểm soát.")
            return {"target": target}

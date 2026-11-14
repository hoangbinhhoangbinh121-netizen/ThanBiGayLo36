"""Nhiệm vụ, thống kê, thành tựu, bảng xếp hạng. Tất cả lắng nghe EventBus nên mọi hệ thống đều liên kết."""
from __future__ import annotations

import json

from core.errors import GameError
from data.basics import ACHIEVEMENTS, QUESTS
from engine.economy import apply_effects
from engine.players import Service

KIND_TO_STAT = {
    "explored": "explores", "clue_found": "clues", "encounter_survived": "survives", "ghost_sealed": "seals",
    "bound": "binds", "died": "deaths", "lost_control": "lost_control", "awakened": "awakens",
    "event_joined": "events", "trade_done": "trades", "report_approved": "reports", "handed_over": "handovers",
    "quest_done": "quests", "level_up": "level_ups", "resurrected": "resurrections",
}
KIND_TO_OBJ = {
    "explored": "explore", "clue_found": "clue", "item_gained": "loot", "encounter_survived": "survive",
    "ghost_sealed": "seal", "bound": "bind", "event_joined": "event", "report_submitted": "report",
}


def match_objective(obj: dict, kind: str, data: dict) -> int:
    """Trả mức tăng tiến độ (0 nếu sự kiện không khớp mục tiêu)."""
    if KIND_TO_OBJ.get(kind) != obj["type"]:
        return 0
    if obj.get("loc") and obj["loc"] != data.get("loc"):
        return 0
    if obj.get("ghost") and obj["ghost"] != data.get("ghost"):
        return 0
    if obj.get("item") and obj["item"] != data.get("item"):
        return 0
    return int(data.get("qty", 1)) if obj["type"] == "loot" else 1


class ProgressService(Service):
    # ---- thống kê & thành tựu ------------------------------------------------------
    def stat(self, uid, key) -> int:
        return self.db.scalar("SELECT value FROM stats WHERE user_id=? AND key=?", (uid, key), 0)

    def inc(self, uid, key, n=1):
        self.db.run("INSERT INTO stats(user_id,key,value) VALUES(?,?,?) "
                    "ON CONFLICT(user_id,key) DO UPDATE SET value=value+excluded.value", (uid, key, n))

    def on_event(self, kind, uid, data):
        if uid is None:
            return
        key = KIND_TO_STAT.get(kind)
        if not key:
            return
        self.inc(uid, key)
        for aid, a in ACHIEVEMENTS.items():
            if a["stat"] != key or self.stat(uid, key) < a["target"]:
                continue
            cur = self.db.run("INSERT OR IGNORE INTO player_achievements(user_id,ach_id,ts) VALUES(?,?,?)",
                              (uid, aid, self.clock.now()))
            if cur.rowcount:
                self.g.players.log(uid, "achievement", f"Thành tựu: {a['name']}.")
                self.g.notify(uid, f"Thành tựu mới: **{a['name']}**")
                apply_effects(self.g, uid, a["reward"], f"Thành tựu {a['name']}")

    def achievements(self, uid):
        have = {r["ach_id"] for r in self.db.all("SELECT ach_id FROM player_achievements WHERE user_id=?", (uid,))}
        return [(aid, a, aid in have, min(self.stat(uid, a["stat"]), a["target"])) for aid, a in ACHIEVEMENTS.items()]

    # ---- bảng xếp hạng ----------------------------------------------------------------
    def board(self, kind: str, limit=10):
        q = {
            "level": "SELECT name, level*1000+exp/10 AS v, 'Cấp '||level AS label FROM players ORDER BY v DESC",
            "reputation": "SELECT name, reputation AS v, reputation||' danh tiếng' AS label FROM players ORDER BY v DESC",
            "seals": "SELECT p.name, s.value AS v, s.value||' lệ quỷ' AS label FROM stats s JOIN players p USING(user_id) "
                     "WHERE s.key='seals' ORDER BY v DESC",
            "clues": "SELECT p.name, s.value AS v, s.value||' manh mối' AS label FROM stats s JOIN players p USING(user_id) "
                     "WHERE s.key='clues' ORDER BY v DESC",
            "contribution": "SELECT p.name, m.contribution AS v, m.contribution||' điểm cống hiến' AS label "
                            "FROM org_members m JOIN players p USING(user_id) ORDER BY v DESC",
        }.get(kind)
        if not q:
            raise GameError("Bảng xếp hạng không tồn tại.")
        return [(r["name"], r["label"]) for r in self.db.all(q + " LIMIT ?", (limit,))]


class QuestService(Service):
    def board(self, uid):
        p = self.g.players.get(uid)
        mine = {r["quest_id"]: r for r in self.db.all("SELECT * FROM quests WHERE user_id=?", (uid,))}
        out = []
        for qid, q in QUESTS.items():
            r = mine.get(qid)
            out.append({"id": qid, "q": q, "status": r["status"] if r else "open",
                        "progress": r["progress"] if r else 0, "locked": p["level"] < q["min_level"]})
        return out

    def accept(self, uid, qid):
        q = QUESTS.get(qid)
        if not q:
            raise GameError("Nhiệm vụ không tồn tại.")
        with self.db.tx():
            p = self.g.players.get(uid)
            if p["level"] < q["min_level"]:
                raise GameError(f"Cần đạt cấp {q['min_level']}.")
            if self.db.one("SELECT 1 FROM quests WHERE user_id=? AND quest_id=?", (uid, qid)):
                raise GameError("Bạn đã nhận nhiệm vụ này rồi.")
            if self.db.scalar("SELECT COUNT(*) FROM quests WHERE user_id=? AND status='active'", (uid,), 0) >= 5:
                raise GameError("Bạn chỉ làm được tối đa 5 nhiệm vụ cùng lúc.")
            self.db.run("INSERT INTO quests(user_id,quest_id,accepted_at) VALUES(?,?,?)", (uid, qid, self.clock.now()))
            self.g.players.log(uid, "quest", f"Nhận nhiệm vụ: {q['name']}.")

    def on_event(self, kind, uid, data):
        if uid is None or kind not in KIND_TO_OBJ:
            return
        for r in self.db.all("SELECT * FROM quests WHERE user_id=? AND status='active'", (uid,)):
            q = QUESTS[r["quest_id"]]
            inc = match_objective(q["obj"], kind, data)
            if not inc:
                continue
            prog = r["progress"] + inc
            if prog >= q["obj"]["n"]:
                self.db.run("UPDATE quests SET progress=?,status='done',completed_at=? WHERE id=?",
                            (q["obj"]["n"], self.clock.now(), r["id"]))
                self.g.players.log(uid, "quest", f"Hoàn thành nhiệm vụ: {q['name']}.")
                self.g.notify(uid, f"Hoàn thành nhiệm vụ **{q['name']}**!")
                apply_effects(self.g, uid, q["reward"], f"Nhiệm vụ {q['name']}")
                self.bus.emit("quest_done", uid, quest=r["quest_id"])
            else:
                self.db.run("UPDATE quests SET progress=? WHERE id=?", (prog, r["id"]))
        self.g.orgs.on_event(kind, uid, data)

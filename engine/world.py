"""Thế giới: trạng thái địa điểm, phong tỏa, di chuyển, hệ số toàn cục từ sự kiện."""
from __future__ import annotations

from core.errors import GameError
from data.events import EVENT_DEFS
from data.locations import HUB, LOCATIONS
from engine.players import Service


class WorldService(Service):
    # ---- trạng thái địa điểm -------------------------------------------------
    def _row(self, loc):
        self.db.run("INSERT OR IGNORE INTO location_state(location_id) VALUES(?)", (loc,))
        return self.db.one("SELECT * FROM location_state WHERE location_id=?", (loc,))

    def modifiers(self) -> dict:
        mods = {"danger_add": 0, "clue_bonus": 0.0, "encounter_add": 0, "loot_mult": 1.0}
        rows = self.db.all("SELECT def_id FROM world_events WHERE kind='global' AND state='active' AND ends_at>?",
                           (self.clock.now(),))
        for ev in rows:
            m = EVENT_DEFS[ev["def_id"]].get("mods", {})
            mods["danger_add"] += m.get("danger_add", 0)
            mods["clue_bonus"] += m.get("clue_bonus", 0.0)
            mods["encounter_add"] += m.get("encounter_add", 0)
            mods["loot_mult"] *= m.get("loot_mult", 1.0)
        return mods

    def unlocked_by_events(self) -> set:
        out = set()
        rows = self.db.all("SELECT def_id FROM world_events WHERE kind='timed' AND state='active' AND ends_at>?",
                           (self.clock.now(),))
        for ev in rows:
            u = EVENT_DEFS[ev["def_id"]].get("unlocks")
            if u:
                out.add(u)
        return out

    def effective_danger(self, loc) -> int:
        base = LOCATIONS[loc]["danger"]
        return max(1, base + self._row(loc)["danger_mod"] + self.modifiers()["danger_add"])

    def lock_info(self, loc):
        r = self._row(loc)
        left = r["locked_until"] - self.clock.now()
        return (True, r["lock_reason"], left) if left > 0 else (False, "", 0)

    def lock(self, loc, seconds, reason="Bị phong tỏa"):
        until = self.clock.now() + int(seconds)
        self._row(loc)
        self.db.run("UPDATE location_state SET locked_until=MAX(locked_until,?),lock_reason=? WHERE location_id=?",
                    (until, reason, loc))

    def unlock(self, loc):
        self._row(loc)
        self.db.run("UPDATE location_state SET locked_until=0,lock_reason='' WHERE location_id=?", (loc,))

    def add_danger_mod(self, loc, n):
        self._row(loc)
        self.db.run("UPDATE location_state SET danger_mod=MAX(-3,MIN(5,danger_mod+?)) WHERE location_id=?", (n, loc))

    def unrest(self) -> int:
        return int(self.db.scalar("SELECT value FROM world_state WHERE key='unrest'", default=0))

    def add_unrest(self, n):
        v = max(0, min(100, self.unrest() + int(n)))
        self.db.run("INSERT INTO world_state(key,value) VALUES('unrest',?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(v),))
        return v

    def apply_world_effects(self, w: dict):
        if "unrest" in w:
            self.add_unrest(w["unrest"])
        for loc, n in w.get("danger_mod", {}).items():
            self.add_danger_mod(loc, n)
        for loc, sec in w.get("lock", {}).items():
            self.lock(loc, sec, "Phong tỏa theo lệnh Tổng Bộ")
        sg = w.get("spawn_ghost")
        if sg:
            self.g.ghosts.free_instance(sg["loc"], sg["ghost"])

    def overview(self):
        active = self.unlocked_by_events()
        out = []
        for lid, loc in LOCATIONS.items():
            if loc.get("requires_event") and lid not in active:
                continue
            locked, reason, left = self.lock_info(lid)
            out.append({"id": lid, "loc": loc, "danger": self.effective_danger(lid),
                        "locked": locked, "reason": reason, "left": left})
        return out

    # ---- di chuyển ---------------------------------------------------------------
    def neighbors(self, loc_id) -> list[str]:
        links = list(LOCATIONS[loc_id]["links"])
        if loc_id == HUB:
            links += [x for x in sorted(self.unlocked_by_events()) if x not in links]
        return links

    def travel(self, uid, dest):
        with self.db.tx():
            p = self.g.players.require_free(uid)
            cur = p["location_id"]
            loc = LOCATIONS.get(dest)
            if not loc:
                raise GameError("Địa điểm không tồn tại.")
            if dest == cur:
                raise GameError("Bạn đang ở đây rồi.")
            if dest not in self.neighbors(cur):
                raise GameError("Không có đường đi trực tiếp tới đó từ chỗ bạn đang đứng.")
            if loc.get("requires_event") and dest not in self.unlocked_by_events():
                raise GameError("Nơi này hiện không tồn tại trên bản đồ.")
            if p["level"] < loc.get("min_level", 1):
                raise GameError(f"Cần đạt cấp {loc['min_level']} để tới {loc['name']}.")
            if loc.get("requires_org") and not self.g.orgs.member(uid):
                raise GameError("Chỉ thành viên Tổng Bộ mới được qua chốt phong tỏa.")
            locked, reason, left = self.lock_info(dest)
            if locked:
                raise GameError(f"{loc['name']} đang bị phong tỏa ({reason}), còn khoảng {left // 60 + 1} phút.")
            cost = 2 + self.effective_danger(dest) // 3
            if p["sanity"] <= cost:
                raise GameError("Tinh thần quá yếu để đi tiếp. Hãy nghỉ ngơi trước.")
            self.db.run("UPDATE players SET location_id=? WHERE user_id=?", (dest, uid))
            self.g.players.adjust(uid, sanity=-cost)
            self.g.players.log(uid, "move", f"Di chuyển tới {loc['name']}.")
            self.bus.emit("moved", uid, loc=dest)
            return cost

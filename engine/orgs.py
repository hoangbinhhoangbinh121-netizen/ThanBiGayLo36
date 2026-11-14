"""Tổ chức Tổng Bộ: cấp bậc, phân quyền, nhiệm vụ tổ chức, báo cáo sự kiện, mở phong tỏa."""
from __future__ import annotations

import json

from core.errors import GameError
from data.basics import MISSION_TYPES, RANKS, REGIONS
from data.ghosts import GHOSTS
from data.locations import LOCATIONS
from engine.economy import apply_effects
from engine.players import Service
from engine.progress import match_objective

ORG_ID = 1
LIFT_COST = 150
MAX_TAKEN = 2
REPORTS_PER_DAY = 3
ARCHIVE_COST = {"thanh_vien": 40, "doi_truong": 20, "phu_trach": 0, "tong_bo": 0}   # phí đọc hồ sơ theo cấp


def rv(rank: str) -> int:
    return RANKS[rank][0]


class OrgService(Service):
    # ---- thành viên -------------------------------------------------------------
    def member(self, uid):
        return self.db.one("SELECT * FROM org_members WHERE user_id=?", (uid,))

    def _need(self, uid, min_rank="thanh_vien"):
        m = self.member(uid)
        if not m:
            raise GameError("Bạn chưa là thành viên Tổng Bộ. Dùng /to_chuc gia_nhap.")
        if rv(m["rank"]) < rv(min_rank):
            raise GameError(f"Cần cấp {RANKS[min_rank][1]} trở lên.")
        return m

    def info(self):
        org = self.db.one("SELECT * FROM orgs WHERE id=?", (ORG_ID,))
        counts = {r["rank"]: r["n"] for r in
                  self.db.all("SELECT rank,COUNT(*) n FROM org_members WHERE org_id=? GROUP BY rank", (ORG_ID,))}
        open_m = self.db.scalar("SELECT COUNT(*) FROM org_missions WHERE status='open' AND deadline>?",
                                (self.clock.now(),), 0)
        vault = self.db.all("SELECT ghost_id,held FROM org_archive WHERE org_id=? AND held>0 ORDER BY ghost_id", (ORG_ID,))
        return {"org": org, "counts": counts, "open_missions": open_m, "vault": vault}

    def add_treasury(self, n):
        self.db.run("UPDATE orgs SET treasury=MAX(0,treasury+?) WHERE id=?", (n, ORG_ID))

    def add_contribution(self, uid, n):
        self.db.run("UPDATE org_members SET contribution=contribution+? WHERE user_id=?", (n, uid))

    def join(self, uid):
        with self.db.tx():
            p = self.g.players.require_free(uid)
            if self.member(uid):
                raise GameError("Bạn đã là thành viên Tổng Bộ.")
            region = LOCATIONS[p["location_id"]]["region"]
            self.db.run("INSERT INTO org_members(org_id,user_id,rank,region,joined_at) VALUES(?,?,?,?,?)",
                        (ORG_ID, uid, "thanh_vien", region, self.clock.now()))
            self.g.players.log(uid, "org", "Gia nhập Tổng Bộ Linh Dị.")

    def leave(self, uid):
        with self.db.tx():
            m = self._need(uid)
            if m["rank"] == "tong_bo" and self.db.scalar(
                    "SELECT COUNT(*) FROM org_members WHERE rank='tong_bo'", default=0) <= 1:
                raise GameError("Bạn là Tổng Bộ duy nhất, hãy bổ nhiệm người kế nhiệm trước.")
            self.db.run("DELETE FROM org_members WHERE user_id=?", (uid,))
            self.g.players.log(uid, "org", "Rời Tổng Bộ Linh Dị.")

    def members(self, limit=25):
        return self.db.all(
            "SELECT m.*,p.name,p.reputation FROM org_members m JOIN players p USING(user_id) "
            "ORDER BY CASE m.rank WHEN 'tong_bo' THEN 4 WHEN 'phu_trach' THEN 3 WHEN 'doi_truong' THEN 2 ELSE 1 END DESC,"
            "m.contribution DESC LIMIT ?", (limit,))

    # ---- phân quyền thăng/giáng ----------------------------------------------------
    def promote(self, actor, target, new_rank=None, region=None):
        with self.db.tx():
            a = self._need(actor, "phu_trach")
            t = self.member(target)
            if not t:
                raise GameError("Người này chưa là thành viên Tổng Bộ.")
            order = sorted(RANKS, key=rv)
            new_rank = new_rank or order[min(order.index(t["rank"]) + 1, len(order) - 1)]
            if new_rank not in RANKS or rv(new_rank) <= rv(t["rank"]):
                raise GameError("Cấp mới phải cao hơn cấp hiện tại.")
            if rv(a["rank"]) <= rv(new_rank):
                raise GameError("Bạn chỉ thăng được cho người khác lên cấp THẤP HƠN cấp của bạn.")
            need = RANKS[new_rank][2]
            rep = self.g.players.get(target)["reputation"]
            if rep < need:
                raise GameError(f"Người này cần {need} danh tiếng để lên {RANKS[new_rank][1]} (hiện {rep}).")
            if new_rank == "phu_trach":
                region = region or t["region"]
                if region not in REGIONS:
                    raise GameError("Người phụ trách khu vực phải có khu vực hợp lệ.")
            else:
                region = t["region"]
            if a["rank"] != "tong_bo" and region != a["region"]:
                raise GameError("Bạn chỉ quản lý được thành viên trong khu vực của mình.")
            self.db.run("UPDATE org_members SET rank=?,region=? WHERE user_id=?", (new_rank, region, target))
            self.g.players.log(target, "org", f"Được thăng làm {RANKS[new_rank][1]}.")
            self.g.notify(target, f"Bạn được thăng làm **{RANKS[new_rank][1]}**.")
            return new_rank

    def demote(self, actor, target):
        with self.db.tx():
            a = self._need(actor, "phu_trach")
            t = self.member(target)
            if not t:
                raise GameError("Người này chưa là thành viên Tổng Bộ.")
            if rv(a["rank"]) <= rv(t["rank"]):
                raise GameError("Bạn chỉ giáng chức được người có cấp thấp hơn bạn.")
            order = sorted(RANKS, key=rv)
            idx = order.index(t["rank"])
            if idx == 0:
                raise GameError("Người này đã ở cấp thấp nhất.")
            self.db.run("UPDATE org_members SET rank=? WHERE user_id=?", (order[idx - 1], target))
            self.g.players.log(target, "org", f"Bị giáng xuống {RANKS[order[idx - 1]][1]}.")
            return order[idx - 1]

    def kick(self, actor, target):
        with self.db.tx():
            a = self._need(actor, "phu_trach")
            t = self.member(target)
            if not t or rv(a["rank"]) <= rv(t["rank"]):
                raise GameError("Bạn không có quyền loại người này.")
            self.db.run("DELETE FROM org_members WHERE user_id=?", (target,))
            self.g.players.log(target, "org", "Bị loại khỏi Tổng Bộ.")

    def set_region(self, actor, target, region):
        with self.db.tx():
            a = self._need(actor, "phu_trach")
            t = self.member(target)
            if not t or region not in REGIONS:
                raise GameError("Thành viên hoặc khu vực không hợp lệ.")
            if a["rank"] != "tong_bo" and (region != a["region"] or t["region"] != a["region"]):
                raise GameError("Bạn chỉ điều động trong khu vực của mình.")
            self.db.run("UPDATE org_members SET region=? WHERE user_id=?", (region, target))

    def appoint_head(self, target):
        """Quyền quản trị bot: bổ nhiệm Tổng Bộ."""
        with self.db.tx():
            self.g.players.get(target)
            if not self.member(target):
                self.db.run("INSERT INTO org_members(org_id,user_id,rank,region,joined_at) VALUES(?,?,?,?,?)",
                            (ORG_ID, target, "tong_bo", "noi_thanh", self.clock.now()))
            else:
                self.db.run("UPDATE org_members SET rank='tong_bo' WHERE user_id=?", (target,))
            self.g.players.log(target, "org", "Được bổ nhiệm Tổng Bộ.")

    def contribute(self, uid, coins):
        if coins < 1:
            raise GameError("Số tiền phải dương.")
        with self.db.tx():
            self._need(uid)
            self.g.players.require_free(uid)
            if self.g.players.get(uid)["coins"] < coins:
                raise GameError("Bạn không đủ tiền cổ.")
            self.g.players.adjust(uid, coins=-coins, rep=coins // 50)
            self.add_treasury(coins)
            self.add_contribution(uid, coins // 5)

    # ---- nhiệm vụ tổ chức -----------------------------------------------------------
    def issue_mission(self, actor, otype, n, reward_coins, region=None, assignee=None, hours=24, loc=None, ghost=None):
        if otype not in MISSION_TYPES or not 1 <= n <= 10 or not 1 <= hours <= 72 or reward_coins < 0:
            raise GameError("Thông số nhiệm vụ không hợp lệ.")
        with self.db.tx():
            a = self._need(actor, "doi_truong")
            if region and region not in REGIONS:
                raise GameError("Khu vực không hợp lệ.")
            if a["rank"] != "tong_bo" and region and region != a["region"]:
                raise GameError("Bạn chỉ giao nhiệm vụ trong khu vực của mình.")
            if assignee is not None and not self.member(assignee):
                raise GameError("Người được giao chưa là thành viên Tổng Bộ.")
            treasury = self.db.scalar("SELECT treasury FROM orgs WHERE id=?", (ORG_ID,), 0)
            if reward_coins > treasury:
                raise GameError(f"Ngân quỹ Tổng Bộ chỉ còn {treasury} tiền cổ.")
            self.add_treasury(-reward_coins)
            now = self.clock.now()
            obj = {"type": otype, "n": n, "loc": loc, "ghost": ghost}
            title = f"{MISSION_TYPES[otype]} x{n}" + (f" tại {LOCATIONS[loc]['name']}" if loc else "")
            cur = self.db.run(
                "INSERT INTO org_missions(org_id,title,objective_json,reward_json,escrow,issued_by,assigned_to,region,"
                "created_at,deadline) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (ORG_ID, title, json.dumps(obj), json.dumps({"coins": reward_coins, "rep": 2 + n}), reward_coins,
                 actor, assignee, region, now, now + hours * 3600))
            return cur.lastrowid

    def missions(self, uid):
        m = self._need(uid)
        now = self.clock.now()
        return self.db.all(
            "SELECT * FROM org_missions WHERE deadline>? AND ("
            " (status='open' AND (assigned_to IS NULL OR assigned_to=?) AND (region IS NULL OR region=?))"
            " OR (status='taken' AND assigned_to=?)) ORDER BY id LIMIT 15", (now, uid, m["region"], uid))

    def take_mission(self, uid, mid):
        with self.db.tx():
            m = self._need(uid)
            r = self.db.one("SELECT * FROM org_missions WHERE id=?", (mid,))
            if not r or r["status"] != "open" or r["deadline"] <= self.clock.now():
                raise GameError("Nhiệm vụ không còn khả dụng.")
            if r["assigned_to"] not in (None, uid):
                raise GameError("Nhiệm vụ này đã giao cho người khác.")
            if r["region"] and r["region"] != m["region"]:
                raise GameError("Nhiệm vụ thuộc khu vực khác.")
            if self.db.scalar("SELECT COUNT(*) FROM org_missions WHERE assigned_to=? AND status='taken'", (uid,), 0) \
                    >= MAX_TAKEN:
                raise GameError(f"Bạn chỉ nhận tối đa {MAX_TAKEN} nhiệm vụ tổ chức cùng lúc.")
            self.db.run("UPDATE org_missions SET status='taken',assigned_to=? WHERE id=?", (uid, mid))

    def on_event(self, kind, uid, data):
        for r in self.db.all("SELECT * FROM org_missions WHERE assigned_to=? AND status='taken'", (uid,)):
            obj = json.loads(r["objective_json"])
            inc = match_objective(obj, kind, data)
            if not inc:
                continue
            prog = r["progress"] + inc
            if prog >= obj["n"]:
                self.db.run("UPDATE org_missions SET progress=?,status='done',escrow=0 WHERE id=?", (obj["n"], r["id"]))
                apply_effects(self.g, uid, json.loads(r["reward_json"]), f"Nhiệm vụ tổ chức #{r['id']}")
                self.add_contribution(uid, 5 + 2 * obj["n"])
                self.g.players.log(uid, "org", f"Hoàn thành nhiệm vụ tổ chức: {r['title']}.")
                self.g.notify(uid, f"Hoàn thành nhiệm vụ tổ chức **{r['title']}**!")
            else:
                self.db.run("UPDATE org_missions SET progress=? WHERE id=?", (prog, r["id"]))

    def expire_missions(self):
        for r in self.db.all("SELECT * FROM org_missions WHERE status IN ('open','taken') AND deadline<=?",
                             (self.clock.now(),)):
            self.add_treasury(r["escrow"])
            self.db.run("UPDATE org_missions SET status='expired',escrow=0 WHERE id=?", (r["id"],))

    # ---- báo cáo sự kiện ---------------------------------------------------------------
    def submit_report(self, uid, text, event_id=None):
        text = text.strip()
        if not 10 <= len(text) <= 500:
            raise GameError("Báo cáo cần từ 10 đến 500 ký tự.")
        with self.db.tx():
            self._need(uid)
            p = self.g.players.get(uid)
            day = self.db.scalar("SELECT COUNT(*) FROM org_reports WHERE author_id=? AND created_at>?",
                                 (uid, self.clock.now() - 86400), 0)
            if day >= REPORTS_PER_DAY:
                raise GameError(f"Mỗi ngày chỉ nộp tối đa {REPORTS_PER_DAY} báo cáo.")
            cur = self.db.run("INSERT INTO org_reports(org_id,author_id,location_id,event_id,text,created_at) "
                              "VALUES(?,?,?,?,?,?)", (ORG_ID, uid, p["location_id"], event_id, text, self.clock.now()))
            self.bus.emit("report_submitted", uid)
            return cur.lastrowid

    def pending_reports(self, actor):
        self._need(actor, "phu_trach")
        return self.db.all("SELECT r.*,p.name FROM org_reports r JOIN players p ON p.user_id=r.author_id "
                           "WHERE r.status='pending' ORDER BY r.id LIMIT 10")

    def review_report(self, actor, rid, approve: bool):
        with self.db.tx():
            self._need(actor, "phu_trach")
            r = self.db.one("SELECT * FROM org_reports WHERE id=? AND status='pending'", (rid,))
            if not r:
                raise GameError("Không có báo cáo đang chờ với mã này.")
            if r["author_id"] == actor:
                raise GameError("Không tự duyệt báo cáo của chính mình.")
            self.db.run("UPDATE org_reports SET status=?,reviewed_by=? WHERE id=?",
                        ("approved" if approve else "rejected", actor, rid))
            if approve:
                coins = 30 if self.db.scalar("SELECT treasury FROM orgs WHERE id=?", (ORG_ID,), 0) >= 30 else 0
                self.add_treasury(-coins)
                apply_effects(self.g, r["author_id"], {"rep": 3, "coins": coins}, "Báo cáo được duyệt")
                self.add_contribution(r["author_id"], 5)
                self.bus.emit("report_approved", r["author_id"])
                self.g.notify(r["author_id"], f"Báo cáo #{rid} của bạn đã được duyệt.")

    # ---- mở phong tỏa ----------------------------------------------------------------------
    def lift_lock(self, actor, loc_id):
        with self.db.tx():
            a = self._need(actor, "phu_trach")
            loc = LOCATIONS.get(loc_id)
            if not loc:
                raise GameError("Địa điểm không tồn tại.")
            if a["rank"] != "tong_bo" and loc["region"] != a["region"]:
                raise GameError("Bạn chỉ mở phong tỏa trong khu vực của mình.")
            if not self.g.world.lock_info(loc_id)[0]:
                raise GameError("Nơi này không bị phong tỏa.")
            treasury = self.db.scalar("SELECT treasury FROM orgs WHERE id=?", (ORG_ID,), 0)
            if treasury < LIFT_COST:
                raise GameError(f"Ngân quỹ cần {LIFT_COST} tiền cổ để điều đội tháo phong tỏa.")
            self.add_treasury(-LIFT_COST)
            self.g.world.unlock(loc_id)
            self.g.players.log(actor, "org", f"Mở phong tỏa {loc['name']}.")

    # ---- hồ sơ linh dị & kho giam giữ ---------------------------------------------------
    def archive_add(self, ghost_id, uid):
        """Ghi lệ quỷ vừa được bàn giao vào kho giam giữ và hồ sơ của Tổng Bộ."""
        self.db.run(
            "INSERT INTO org_archive(org_id,ghost_id,held,total_handed,first_by,first_at) VALUES(?,?,1,1,?,?) "
            "ON CONFLICT(org_id,ghost_id) DO UPDATE SET held=held+1,total_handed=total_handed+1",
            (ORG_ID, ghost_id, uid, self.clock.now()))

    def archive_list(self, uid):
        """Danh sách hồ sơ + số manh mối bạn đã nắm. Chỉ thành viên xem được."""
        m = self._need(uid)
        rows = self.db.all("SELECT * FROM org_archive WHERE org_id=? ORDER BY ghost_id", (ORG_ID,))
        return {"rows": [{"row": r, "known": len(self.g.ghosts.clues_known(uid, r["ghost_id"]))} for r in rows],
                "cost": ARCHIVE_COST[m["rank"]]}

    def read_archive(self, uid, ghost_id) -> dict:
        """Đọc hồ sơ: nhận manh mối chưa biết tiếp theo về một lệ quỷ mà Tổng Bộ đã từng thu giữ."""
        if ghost_id not in GHOSTS:
            raise GameError("Lệ quỷ không tồn tại.")
        with self.db.tx():
            m = self._need(uid)
            self.g.players.require_free(uid)
            if not self.db.one("SELECT 1 FROM org_archive WHERE org_id=? AND ghost_id=?", (ORG_ID, ghost_id)):
                raise GameError("Tổng Bộ chưa từng thu giữ lệ quỷ này nên chưa có hồ sơ. "
                                "Hãy bàn giao một Vật Chứa Vàng chứa nó để mở hồ sơ.")
            idx = self.g.ghosts.unknown_clue(uid, ghost_id)
            if idx is None:
                raise GameError("Bạn đã nắm toàn bộ manh mối trong hồ sơ này.")
            cost = ARCHIVE_COST[m["rank"]]
            if self.g.players.get(uid)["coins"] < cost:
                raise GameError(f"Phí đọc hồ sơ là {cost} tiền cổ.")
            self.g.players.check_cooldown(uid, "archive", 60)
            if cost:
                self.g.players.adjust(uid, coins=-cost)
            self.g.ghosts.add_clue(uid, ghost_id, idx)
            return {"ghost": ghost_id, "idx": idx, "text": GHOSTS[ghost_id]["clues"][idx], "cost": cost}

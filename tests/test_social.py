import unittest

from core.errors import GameError
from tests.helpers import make_game, mkplayer


class OrgTests(unittest.TestCase):
    def setUp(self):
        g = self.g = make_game(41)
        for uid in (1, 2, 3, 4):
            mkplayer(g, uid, name=f"Pk{uid}", loc="thanh_pho")
        g.orgs.appoint_head(1)
        for uid in (2, 3, 4):
            g.orgs.join(uid)

    def rep(self, uid, n):
        self.g.db.run("UPDATE players SET reputation=? WHERE user_id=?", (n, uid))

    def test_rank_permissions(self):
        g = self.g
        with self.assertRaises(GameError):
            g.orgs.promote(2, 3)                 # thành viên không có quyền
        with self.assertRaises(GameError):
            g.orgs.promote(1, 3)                 # thiếu danh tiếng
        self.rep(3, 25)
        self.assertEqual(g.orgs.promote(1, 3), "doi_truong")
        self.rep(3, 70)
        self.assertEqual(g.orgs.promote(1, 3), "phu_trach")
        with self.assertRaises(GameError):
            g.orgs.promote(1, 3, "tong_bo")      # không thăng ngang cấp mình
        self.rep(4, 25)
        g.orgs.promote(3, 4)                     # phụ trách thăng được đội trưởng (cùng khu vực)
        with self.assertRaises(GameError):
            g.orgs.promote(3, 2, "phu_trach")    # không thăng lên cấp bằng mình
        with self.assertRaises(GameError):
            g.orgs.demote(4, 3)                  # cấp thấp hơn không giáng được cấp cao
        self.assertEqual(g.orgs.demote(1, 4), "thanh_vien")

    def test_last_head_cannot_leave(self):
        with self.assertRaises(GameError):
            self.g.orgs.leave(1)

    def test_mission_escrow_progress_reward_and_expiry(self):
        g = self.g
        self.rep(2, 25)
        g.orgs.promote(1, 2)
        treasury = g.db.scalar("SELECT treasury FROM orgs")
        with self.assertRaises(GameError):
            g.orgs.issue_mission(3, "clue", 2, 10)           # thành viên không giao được
        with self.assertRaises(GameError):
            g.orgs.issue_mission(2, "clue", 2, treasury + 1)  # vượt ngân quỹ
        mid = g.orgs.issue_mission(2, "clue", 2, 100)
        self.assertEqual(g.db.scalar("SELECT treasury FROM orgs"), treasury - 100)
        self.assertEqual([m["id"] for m in g.orgs.missions(3)], [mid])
        g.orgs.take_mission(3, mid)
        with self.assertRaises(GameError):
            g.orgs.take_mission(4, mid)
        coins = g.players.get(3)["coins"]
        g.ghosts.add_clue(3, "quy_mon", 0)
        g.ghosts.add_clue(3, "quy_mon", 1)
        self.assertEqual(g.db.one("SELECT status FROM org_missions WHERE id=?", (mid,))["status"], "done")
        self.assertEqual(g.players.get(3)["coins"], coins + 100)
        self.assertGreater(g.orgs.member(3)["contribution"], 0)
        mid2 = g.orgs.issue_mission(2, "explore", 1, 50)
        g.clock.advance(25 * 3600)
        t = g.db.scalar("SELECT treasury FROM orgs")
        g.orgs.expire_missions()
        self.assertEqual(g.db.scalar("SELECT treasury FROM orgs"), t + 50)

    def test_regional_mission_visibility(self):
        g = self.g
        mid = g.orgs.issue_mission(1, "survive", 1, 10, region="ngoai_o")
        self.assertEqual(g.orgs.missions(2), [])
        g.orgs.set_region(1, 2, "ngoai_o")
        self.assertEqual([m["id"] for m in g.orgs.missions(2)], [mid])

    def test_reports_review_flow(self):
        g = self.g
        with self.assertRaises(GameError):
            g.orgs.submit_report(2, "ngắn")
        rid = g.orgs.submit_report(2, "Phát hiện tiếng gõ cửa lúc nửa đêm ở tầng 7.")
        with self.assertRaises(GameError):
            g.orgs.review_report(2, rid, True)       # thành viên không duyệt được
        g.orgs.submit_report(1, "Báo cáo của chính Tổng Bộ để thử tự duyệt.")
        own = g.db.one("SELECT id FROM org_reports WHERE author_id=1")["id"]
        with self.assertRaises(GameError):
            g.orgs.review_report(1, own, True)       # không tự duyệt
        rep = g.players.get(2)["reputation"]
        g.orgs.review_report(1, rid, True)
        self.assertEqual(g.players.get(2)["reputation"], rep + 3)
        self.assertEqual(g.progress.stat(2, "reports"), 1)
        with self.assertRaises(GameError):
            g.orgs.review_report(1, rid, True)       # đã duyệt
        for _ in range(2):
            g.orgs.submit_report(2, "Một báo cáo nữa đủ dài để hợp lệ.")
        with self.assertRaises(GameError):
            g.orgs.submit_report(2, "Báo cáo thứ tư trong ngày bị chặn.")

    def test_lift_lock_costs_treasury_and_respects_region(self):
        g = self.g
        g.world.lock("khu_dan_cu", 3600, "x")
        with self.assertRaises(GameError):
            g.orgs.lift_lock(2, "khu_dan_cu")
        t = g.db.scalar("SELECT treasury FROM orgs")
        g.orgs.lift_lock(1, "khu_dan_cu")
        self.assertFalse(g.world.lock_info("khu_dan_cu")[0])
        self.assertEqual(g.db.scalar("SELECT treasury FROM orgs"), t - 150)
        with self.assertRaises(GameError):
            g.orgs.lift_lock(1, "khu_dan_cu")

    def test_contribute_and_leaderboards(self):
        g = self.g
        g.orgs.contribute(2, 60)
        self.assertEqual(g.orgs.member(2)["contribution"], 12)
        top = g.progress.board("contribution")
        self.assertEqual(top[0][0], "Pk2")
        for kind in ("level", "reputation", "seals", "clues", "contribution"):
            g.progress.board(kind)
        with self.assertRaises(GameError):
            g.progress.board("khong_co")


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        g = self.g = make_game(71)
        for uid, n in ((1, "Tong Bo"), (2, "Thanh Vien"), (3, "Ngoai Nguoi")):
            mkplayer(g, uid, name=n, loc="thanh_pho", coins=300)
        g.orgs.appoint_head(1)
        g.orgs.join(2)

    def seal_and_hand_over(self, uid, ghost_id):
        g = self.g
        inst = g.ghosts.spawn(ghost_id, "thanh_pho")
        g.inv.add(uid, "vat_chua_vang", 1)
        g.ghosts.seal(uid, inst)
        return g.ghosts.hand_over(uid, inst)

    def test_handover_fills_vault_and_unlocks_archive_for_everyone_in_org(self):
        g = self.g
        with self.assertRaises(GameError):
            g.orgs.read_archive(2, "quy_mon")                  # chưa ai bàn giao
        self.seal_and_hand_over(1, "quy_mon")
        self.seal_and_hand_over(1, "quy_mon")
        info = g.orgs.info()
        self.assertEqual([(v["ghost_id"], v["held"]) for v in info["vault"]], [("quy_mon", 2)])
        data = g.orgs.archive_list(2)
        self.assertEqual(data["cost"], 40)
        self.assertEqual(data["rows"][0]["row"]["total_handed"], 2)
        coins = g.players.get(2)["coins"]
        r = g.orgs.read_archive(2, "quy_mon")
        self.assertEqual((r["idx"], r["cost"]), (0, 40))
        self.assertEqual(g.players.get(2)["coins"], coins - 40)
        self.assertEqual(g.ghosts.clues_known(2, "quy_mon"), {0})
        with self.assertRaises(GameError):
            g.orgs.read_archive(2, "quy_mon")                  # cooldown 60s
        g.clock.advance(61)
        self.assertEqual(g.orgs.read_archive(2, "quy_mon")["idx"], 1)
        g.clock.advance(61)
        g.orgs.read_archive(2, "quy_mon")
        g.clock.advance(61)
        with self.assertRaises(GameError):
            g.orgs.read_archive(2, "quy_mon")                  # hết manh mối
        self.assertEqual(g.progress.stat(2, "clues"), 3)

    def test_non_member_and_unarchived_ghost_and_poor_player(self):
        g = self.g
        self.seal_and_hand_over(1, "quy_anh")
        with self.assertRaises(GameError):
            g.orgs.read_archive(3, "quy_anh")                  # không thuộc Tổng Bộ
        with self.assertRaises(GameError):
            g.orgs.archive_list(3)
        with self.assertRaises(GameError):
            g.orgs.read_archive(2, "quy_vuc")                  # quỷ này chưa có hồ sơ
        g.db.run("UPDATE players SET coins=10 WHERE user_id=2")
        with self.assertRaises(GameError):
            g.orgs.read_archive(2, "quy_anh")                  # thiếu phí
        self.assertEqual(g.ghosts.clues_known(2, "quy_anh"), set())   # lỗi không để lại tác dụng phụ
        self.assertEqual(g.players.get(2)["coins"], 10)

    def test_rank_discount_head_reads_free(self):
        g = self.g
        self.seal_and_hand_over(1, "quy_nhan")
        coins = g.players.get(1)["coins"]
        r = g.orgs.read_archive(1, "quy_nhan")
        self.assertEqual(r["cost"], 0)
        self.assertEqual(g.players.get(1)["coins"], coins)


class EconomyTests(unittest.TestCase):
    def setUp(self):
        g = self.g = make_game(51)
        mkplayer(g, 1, name="An An", loc="thanh_pho", coins=500)
        mkplayer(g, 2, name="Bao Bao", loc="thanh_pho", coins=100)

    def test_shop_buy_sell_rules(self):
        g = self.g
        g.econ.buy(1, "bang_gac", 2)
        self.assertEqual(g.players.get(1)["coins"], 450)
        with self.assertRaises(GameError):
            g.econ.buy(1, "dinh_quan_tai")       # không bán
        with self.assertRaises(GameError):
            g.econ.buy(2, "vat_chua_vang")       # thiếu tiền
        with self.assertRaises(GameError):
            g.econ.buy(1, "bang_gac", 99)
        self.assertEqual(g.econ.sell(1, "bang_gac", 1), 8)
        g.db.run("UPDATE players SET location_id='khu_dan_cu' WHERE user_id=1")
        with self.assertRaises(GameError):
            g.econ.buy(1, "bang_gac")            # xa cửa hàng

    def test_rest_heals_cools_down_and_suppresses(self):
        g = self.g
        g.db.run("UPDATE players SET hp=10,sanity=10,corruption=20 WHERE user_id=1")
        inst = g.ghosts.spawn("quy_mon", "thanh_pho")
        g.rng.forced = 0.0
        g.ghosts.bind(1, inst)
        g.rng.forced = None
        g.econ.rest(1)
        p = g.players.get(1)
        self.assertGreater(p["hp"], 50)
        self.assertEqual(p["corruption"], 15)
        self.assertEqual(g.ghosts.get(inst)["resurrection"], 0)
        with self.assertRaises(GameError):
            g.econ.rest(1)                        # cooldown

    def test_trade_atomic_success(self):
        g = self.g
        g.inv.add(1, "den_dau", 3)
        tid = g.econ.offer(1, 2, {"item": "den_dau", "qty": 2}, {"coins": 60})
        with self.assertRaises(GameError):
            g.econ.accept(1, tid)                 # người gửi không tự nhận
        g.econ.accept(2, tid)
        self.assertEqual((g.inv.count(1, "den_dau"), g.inv.count(2, "den_dau")), (2, 3))  # mỗi người khởi đầu có sẵn 1
        self.assertEqual((g.players.get(1)["coins"], g.players.get(2)["coins"]), (560, 40))
        with self.assertRaises(GameError):
            g.econ.accept(2, tid)                 # không dùng lại

    def test_trade_failure_leaves_everything_untouched(self):
        g = self.g
        g.inv.add(1, "den_dau", 1)
        tid = g.econ.offer(1, 2, {"item": "den_dau", "qty": 1}, {"coins": 900})
        before = (g.players.get(1)["coins"], g.players.get(2)["coins"], g.inv.count(1, "den_dau"))
        with self.assertRaises(GameError):
            g.econ.accept(2, tid)                 # B không đủ tiền
        after = (g.players.get(1)["coins"], g.players.get(2)["coins"], g.inv.count(1, "den_dau"))
        self.assertEqual(before, after)
        g.inv.remove(1, "den_dau", 1)             # A bán mất đồ trước khi B nhận
        tid2 = g.econ.offer(1, 2, {"coins": 10}, {"coins": 0})
        g.db.run("UPDATE players SET coins=0 WHERE user_id=1")
        with self.assertRaises(GameError):
            g.econ.accept(2, tid2)

    def test_trade_validation_and_limits(self):
        g = self.g
        with self.assertRaises(GameError):
            g.econ.offer(1, 1, {"coins": 1}, {})
        with self.assertRaises(GameError):
            g.econ.offer(1, 2, {"item": "den_dau", "qty": 5}, {})   # không có đồ
        with self.assertRaises(GameError):
            g.econ.offer(1, 2, {"coins": -5}, {})
        with self.assertRaises(GameError):
            g.econ.offer(1, 2, {}, {})
        for _ in range(3):
            g.econ.offer(1, 2, {"coins": 1}, {})
        with self.assertRaises(GameError):
            g.econ.offer(1, 2, {"coins": 1}, {})                    # quá 3 lời mời
        g.clock.advance(601)
        self.assertEqual(g.econ.pending_for(2), [])                  # hết hạn
        tid = g.econ.offer(1, 2, {"coins": 1}, {})
        g.econ.decline(2, tid)
        self.assertEqual(g.econ.pending_for(2), [])


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.g = make_game(61)
        mkplayer(self.g, 1, loc="khu_dan_cu")

    def test_quest_completes_from_real_gameplay_events(self):
        g = self.g
        g.quests.accept(1, "q_manh_moi")
        with self.assertRaises(GameError):
            g.quests.accept(1, "q_manh_moi")
        with self.assertRaises(GameError):
            g.quests.accept(1, "q_phong_an")                   # chưa đủ cấp
        for i in range(3):
            g.ghosts.add_clue(1, "quy_anh", i)
        row = g.db.one("SELECT * FROM quests WHERE user_id=1")
        self.assertEqual((row["status"], row["progress"]), ("done", 3))
        self.assertEqual(g.inv.count(1, "thuoc_an_than"), 1)
        self.assertTrue(any("nhiệm vụ" in n for n in g.drain_notices(1)))

    def test_targeted_quest_ignores_wrong_ghost(self):
        g = self.g
        g.db.run("UPDATE players SET level=2 WHERE user_id=1")
        g.quests.accept(1, "q_nghia_trang")
        g.ghosts.add_clue(1, "quy_mon", 0)
        self.assertEqual(g.db.one("SELECT progress FROM quests")["progress"], 0)
        g.ghosts.add_clue(1, "quy_quan_tai", 0)
        g.ghosts.add_clue(1, "quy_quan_tai", 1)
        self.assertEqual(g.inv.count(1, "dinh_quan_tai"), 1)

    def test_loot_quest_counts_quantity_and_achievements_unlock_once(self):
        g = self.g
        g.explore.explore  # liên kết khám phá -> thành tựu
        g.bus.emit("explored", 1, loc="khu_dan_cu")
        g.bus.emit("explored", 1, loc="khu_dan_cu")
        ach = g.db.all("SELECT ach_id FROM player_achievements WHERE user_id=1")
        self.assertEqual([a["ach_id"] for a in ach], ["buoc_dau"])
        self.assertEqual(g.progress.stat(1, "explores"), 2)

    def test_everything_connected_one_explore_updates_quest_stat_history(self):
        g = self.g
        g.quests.accept(1, "q_dieu_tra")
        for _ in range(3):
            g.clock.advance(60)
            g.db.run("UPDATE players SET hp=max_hp,sanity=max_sanity WHERE user_id=1")
            g.db.run("DELETE FROM encounters")
            g.explore.explore(1, "tham_do")
        self.assertEqual(g.db.one("SELECT status FROM quests")["status"], "done")
        self.assertGreaterEqual(len(g.players.history(1)), 3)


if __name__ == "__main__":
    unittest.main()

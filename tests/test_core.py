import tempfile
import unittest
from pathlib import Path

from core.cooldown import Limiter
from core.database import Database
from core.errors import GameError
from tests.helpers import ROOT, FakeClock, make_game, mkplayer


class DatabaseTests(unittest.TestCase):
    def test_migrations_apply_once_and_in_order(self):
        db = Database(":memory:", FakeClock()).connect()
        first = db.migrate(ROOT / "migrations")
        self.assertEqual(first[0], "001_core.sql")
        self.assertEqual(len(first), 5)
        self.assertEqual(db.migrate(ROOT / "migrations"), [])
        self.assertEqual(db.schema_version(), 5)

    def test_foreign_keys_enforced(self):
        g = make_game()
        with self.assertRaises(Exception):
            g.db.run("INSERT INTO inventory(user_id,item_id,qty) VALUES(999,'den_dau',1)")

    def test_tx_rolls_back_and_nested_savepoint(self):
        g = make_game()
        mkplayer(g)
        with self.assertRaises(RuntimeError):
            with g.db.tx():
                g.db.run("UPDATE players SET coins=777 WHERE user_id=1")
                raise RuntimeError
        self.assertNotEqual(g.players.get(1)["coins"], 777)
        with g.db.tx():
            g.db.run("UPDATE players SET coins=11 WHERE user_id=1")
            try:
                with g.db.tx():
                    g.db.run("UPDATE players SET coins=22 WHERE user_id=1")
                    raise RuntimeError
            except RuntimeError:
                pass
        self.assertEqual(g.players.get(1)["coins"], 11)

    def test_backup_creates_valid_copy_and_prunes(self):
        g = make_game()
        mkplayer(g)
        with tempfile.TemporaryDirectory() as d:
            for _ in range(4):
                g.clock.advance(5)
                path = g.db.backup(d, keep=2)
            self.assertEqual(len(list(Path(d).glob("tbpt-*.db"))), 2)
            copy = Database(path).connect()
            self.assertEqual(copy.one("SELECT name FROM players WHERE user_id=1")["name"], "Tester")
            copy.close()


class LimiterTests(unittest.TestCase):
    def test_per_command_cooldown_and_burst_block(self):
        t = [100.0]
        lim = Limiter(burst=5, window=10, block=30, now=lambda: t[0])
        self.assertTrue(lim.hit(1, "a", 2)[0])
        ok, wait = lim.hit(1, "a", 2)
        self.assertFalse(ok)
        self.assertGreater(wait, 1.9)
        t[0] += 2.1
        self.assertTrue(lim.hit(1, "a", 2)[0])
        results = []
        for i in range(10):
            t[0] += 0.2
            results.append(lim.hit(2, f"b{i}", 0)[0])
        self.assertIn(False, results)
        ok, wait = lim.hit(2, "zz", 0)
        self.assertFalse(ok)
        self.assertGreater(wait, 20)
        t[0] += 31
        self.assertTrue(lim.hit(2, "zz", 0)[0])


class LimiterMemoryTests(unittest.TestCase):
    def test_old_entries_are_pruned(self):
        t = [0.0]
        lim = Limiter(now=lambda: t[0])
        for uid in range(400):
            lim.hit(uid, "a", 1)
        t[0] += 7200
        for _ in range(200):
            lim.hit(10_000, "a", 1)
            t[0] += 1.1
        self.assertLess(len(lim._last), 50)
        self.assertLess(len(lim._hist), 50)


class DeleteCharacterTests(unittest.TestCase):
    def test_delete_cleans_ghosts_missions_reports_without_integrity_errors(self):
        g = make_game(3)
        mkplayer(g, 1, name="Nguoi Mot", loc="khu_dan_cu")
        mkplayer(g, 2, name="Nguoi Hai", loc="thanh_pho")
        g.rng.forced = 0.0
        held = g.ghosts.spawn("quy_mon", "khu_dan_cu")
        g.ghosts.bind(1, held)
        g.rng.forced = None
        sealed = g.ghosts.spawn("quy_anh", "khu_dan_cu")
        g.inv.add(1, "vat_chua_vang", 1)
        g.ghosts.seal(1, sealed)
        g.db.run("UPDATE players SET location_id='thanh_pho' WHERE user_id=1")
        g.orgs.appoint_head(1)
        g.orgs.join(2)
        mid = g.orgs.issue_mission(1, "clue", 2, 100)               # ký quỹ 100
        g.orgs.take_mission(2, mid)
        rid = g.orgs.submit_report(2, "Báo cáo đủ dài để được duyệt bởi Tổng Bộ.")
        g.orgs.review_report(1, rid, True)
        treasury = g.db.scalar("SELECT treasury FROM orgs")
        g.db.run("UPDATE players SET location_id='khu_dan_cu' WHERE user_id=1")
        out = g.players.delete(1)
        self.assertEqual((out["ghosts_released"], out["sealed_lost"]), (1, 1))
        self.assertEqual(g.ghosts.get(held)["state"], "free")             # quỷ tuột ra, ở lại nơi đó
        self.assertEqual(g.ghosts.get(held)["location_id"], "khu_dan_cu")
        self.assertEqual(g.db.scalar("SELECT treasury FROM orgs"), treasury + 100)   # hoàn quỹ nhiệm vụ chưa xong
        self.assertIsNone(g.db.one("SELECT 1 FROM org_missions"))
        self.assertIsNone(g.db.one("SELECT reviewed_by FROM org_reports")["reviewed_by"])
        self.assertIsNone(g.db.one("PRAGMA foreign_key_check"))
        with self.assertRaises(GameError):
            g.players.get(1)
        mkplayer(g, 1, name="Nguoi Moi")                                    # tạo lại được

    def test_delete_in_safe_place_dissolves_ghosts_and_requeues_taken_missions(self):
        g = make_game(4)
        mkplayer(g, 1, name="Nguoi Mot", loc="thanh_pho")
        mkplayer(g, 2, name="Nguoi Hai", loc="thanh_pho")
        inst = g.ghosts.spawn("quy_mon", "thanh_pho")
        g.rng.forced = 0.0
        g.ghosts.bind(1, inst)
        g.rng.forced = None
        g.orgs.appoint_head(2)
        g.orgs.join(1)
        mid = g.orgs.issue_mission(2, "explore", 1, 10)
        g.orgs.take_mission(1, mid)
        g.players.delete(1)
        with self.assertRaises(GameError):
            g.ghosts.get(inst)                                              # ở nơi an toàn: lệ quỷ tan biến
        self.assertEqual(g.db.one("SELECT status,assigned_to FROM org_missions")["status"], "open")
        self.assertIsNone(g.db.one("PRAGMA foreign_key_check"))


class PlayerTests(unittest.TestCase):
    def setUp(self):
        self.g = make_game()

    def test_create_validates(self):
        g = self.g
        with self.assertRaises(GameError):
            g.players.create(1, "A", "hoc_sinh")
        with self.assertRaises(GameError):
            g.players.create(1, "Hợp lệ", "khong_co")
        p = g.players.create(1, "  Lâm   Phong ", "y_ta")
        self.assertEqual(p["name"], "Lâm Phong")
        self.assertEqual(p["location_id"], "thanh_pho")
        self.assertEqual(g.inv.count(1, "bang_gac"), 2)
        with self.assertRaises(GameError):
            g.players.create(1, "Lần Hai", "y_ta")
        with self.assertRaises(GameError):
            g.players.get(404)

    def test_level_up(self):
        g = self.g
        mkplayer(g)
        res = g.players.adjust(1, exp=350)
        p = g.players.get(1)
        self.assertEqual(res["level_up"], 2)
        self.assertEqual((p["level"], p["exp"]), (3, 50))
        self.assertEqual(p["max_hp"], 125)

    def test_death_penalty_and_hinh_nhan(self):
        g = self.g
        mkplayer(g, coins=100, loc="benh_vien")
        g.inv.add(1, "hinh_nhan", 1)
        res = g.players.adjust(1, hp=-999)
        self.assertTrue(res["saved"])
        self.assertEqual(g.players.get(1)["hp"], 1)
        self.assertEqual(g.inv.count(1, "hinh_nhan"), 0)
        res = g.players.adjust(1, hp=-999)
        p = g.players.get(1)
        self.assertTrue(res["died"])
        self.assertEqual(p["location_id"], "thanh_pho")
        self.assertEqual(p["coins"], 70)
        self.assertEqual(p["hp"], p["max_hp"] // 2)

    def test_breakdown_blocks_actions_then_expires(self):
        g = self.g
        mkplayer(g, loc="khu_dan_cu")
        res = g.players.adjust(1, sanity=-999)
        self.assertTrue(res["breakdown"])
        self.assertEqual(g.players.get(1)["status"], "mat_kiem_soat")
        with self.assertRaises(GameError):
            g.explore.explore(1, "tham_do")
        g.clock.advance(1000)
        g.players.refresh(1)
        self.assertEqual(g.players.get(1)["status"], "binh_thuong")

    def test_regen_over_time_and_corruption_status(self):
        g = self.g
        mkplayer(g, loc="khu_dan_cu")
        g.db.run("UPDATE players SET hp=50,sanity=50 WHERE user_id=1")
        g.clock.advance(3600 * 5)
        p = g.players.refresh(1)
        self.assertEqual(p["hp"], 70)
        self.assertEqual(p["sanity"], 80)
        g.players.adjust(1, corruption=45)
        self.assertEqual(g.players.get(1)["status"], "nhiem_linh_di")
        g.players.adjust(1, corruption=-20)
        self.assertEqual(g.players.get(1)["status"], "binh_thuong")


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from core.errors import GameError
from data.events import EVENT_DEFS
from data.locations import LOCATIONS
from tests.helpers import make_game, mkplayer


class WorldTests(unittest.TestCase):
    def setUp(self):
        self.g = make_game(11)
        mkplayer(self.g, loc="thanh_pho", level=5, sanity=100)

    def test_location_graph_is_consistent(self):
        for lid, loc in LOCATIONS.items():
            for other in loc["links"]:
                self.assertIn(other, LOCATIONS)
                if loc.get("requires_event") or LOCATIONS[other].get("requires_event"):
                    continue  # lối đi mở động theo sự kiện, kiểm tra riêng ở test sự kiện giới hạn thời gian
                self.assertIn(lid, LOCATIONS[other]["links"], f"{lid}<->{other} không đối xứng")
            for gid in loc["ghosts"]:
                self.assertIn(gid, __import__("data.ghosts", fromlist=["GHOSTS"]).GHOSTS)

    def test_travel_rules(self):
        g = self.g
        with self.assertRaises(GameError):
            g.world.travel(1, "nghia_trang")      # không kề
        with self.assertRaises(GameError):
            g.world.travel(1, "ga_cuoi")          # chưa có sự kiện tàu
        cost = g.world.travel(1, "khu_dan_cu")
        self.assertGreaterEqual(cost, 2)
        self.assertEqual(g.players.get(1)["location_id"], "khu_dan_cu")
        with self.assertRaises(GameError):
            g.world.travel(1, "pho_co")           # cần Tổng Bộ
        g.world.travel(1, "thanh_pho")
        g.orgs.join(1)
        g.world.travel(1, "khu_dan_cu")
        g.world.travel(1, "pho_co")

    def test_lock_blocks_travel_and_explore_then_unlocks(self):
        g = self.g
        g.world.travel(1, "khu_dan_cu")
        g.world.lock("khu_dan_cu", 600, "thử nghiệm")
        with self.assertRaises(GameError):
            g.explore.explore(1, "tham_do")
        g.clock.advance(601)
        g.explore.explore(1, "tham_do")

    def test_min_level_gate(self):
        g = self.g
        g.db.run("UPDATE players SET level=1,location_id='benh_vien' WHERE user_id=1")
        with self.assertRaises(GameError):
            g.world.travel(1, "nghia_trang")


class ExploreTests(unittest.TestCase):
    def setUp(self):
        self.g = make_game(21)
        mkplayer(self.g, loc="khu_dan_cu", sanity=100)

    def test_safe_hub_cannot_be_explored(self):
        g = self.g
        g.db.run("UPDATE players SET location_id='thanh_pho' WHERE user_id=1")
        with self.assertRaises(GameError):
            g.explore.explore(1, "tham_do")

    def test_cost_cooldown_and_low_sanity(self):
        g = self.g
        before = g.players.get(1)["sanity"]
        res = g.explore.explore(1, "tham_do")
        if res["encounter"]:
            g.db.run("DELETE FROM encounters")
        self.assertLess(g.players.get(1)["sanity"], before)
        with self.assertRaises(GameError):
            g.explore.explore(1, "tham_do")   # cooldown
        g.clock.advance(60)
        g.db.run("DELETE FROM encounters")
        g.db.run("UPDATE players SET sanity=4 WHERE user_id=1")
        with self.assertRaises(GameError):
            g.explore.explore(1, "dieu_tra")

    def test_many_explorations_produce_all_kinds_and_stay_consistent(self):
        g = self.g
        kinds = set()
        for i in range(160):
            g.clock.advance(30)
            g.db.run("UPDATE players SET hp=max_hp,sanity=max_sanity,status='binh_thuong',corruption=0 WHERE user_id=1")
            g.db.run("DELETE FROM encounters")
            mode = ("tham_do", "dieu_tra", "tim_do")[i % 3]
            res = g.explore.explore(1, mode)
            kinds.add(res["kind"])
            self.assertTrue(res["lines"])
        self.assertTrue({"loot", "clue", "encounter", "incident", "nothing"} <= kinds, kinds)
        p = g.players.get(1)
        self.assertGreaterEqual(p["hp"], 0)
        self.assertGreater(g.progress.stat(1, "explores"), 100)
        self.assertGreater(g.progress.stat(1, "clues"), 0)

    def test_clues_are_unique_then_exhausted_falls_back_to_loot(self):
        g = self.g
        for gid in ("quy_mon", "quy_anh"):
            for i in range(3):
                g.ghosts.add_clue(1, gid, i)
        res = {"lines": []}
        self.assertFalse(g.explore._clue(1, LOCATIONS["khu_dan_cu"], res))

    def test_sight_buff_forces_clue_and_loot_buff_adds_roll(self):
        g = self.g
        g.players.set_buff(1, "sight", 1)
        res = g.explore.explore(1, "dieu_tra")
        self.assertEqual(res["kind"], "clue")
        self.assertEqual(g.players.buff(1, "sight"), 0)

    def test_domain_buff_reduces_encounters(self):
        base_enc = 0
        for seed in range(3):
            g = make_game(seed)
            mkplayer(g, loc="benh_vien", level=5)
            for _ in range(60):
                g.clock.advance(30)
                g.db.run("UPDATE players SET hp=max_hp,sanity=max_sanity WHERE user_id=1")
                g.db.run("DELETE FROM encounters")
                base_enc += g.explore.explore(1, "tham_do")["encounter"]
        dom_enc = 0
        for seed in range(3):
            g = make_game(seed)
            mkplayer(g, loc="benh_vien", level=5)
            for _ in range(60):
                g.clock.advance(30)
                g.db.run("UPDATE players SET hp=max_hp,sanity=max_sanity WHERE user_id=1")
                g.db.run("DELETE FROM encounters")
                g.players.set_buff(1, "domain", 3)
                dom_enc += g.explore.explore(1, "tham_do")["encounter"]
        self.assertLess(dom_enc, base_enc)


class EventTests(unittest.TestCase):
    def setUp(self):
        self.g = make_game(31)
        for uid in (1, 2, 3):
            mkplayer(self.g, uid, loc="khu_dan_cu", name=f"P{uid}", sanity=100)

    def test_contrib_event_success_rewards_and_ghost_goes_to_top(self):
        g = self.g
        eid = g.events.start_event("quy_xuat_hien", "khu_dan_cu")
        ev = g.events.get(eid)
        self.assertIsNotNone(ev["ghost_instance_id"])
        self.assertEqual(g.world._row("khu_dan_cu")["danger_mod"], 1)
        with self.assertRaises(GameError):
            g.db.run("UPDATE players SET location_id='thanh_pho' WHERE user_id=3")
            g.events.participate(3, eid, "dieu_tra")
        g.db.run("UPDATE players SET location_id='khu_dan_cu' WHERE user_id=3")
        coins2 = g.players.get(2)["coins"]
        done = False
        for _ in range(10):
            g.clock.advance(25)
            for uid in (1, 2):
                if not done:
                    r = g.events.participate(uid, eid, "dieu_tra" if uid == 2 else "so_tan")
                    done = r["done"]
            g.db.run("UPDATE players SET sanity=100,hp=max_hp")
        self.assertTrue(done)
        self.assertEqual(g.events.get(eid)["state"], "resolved")
        self.assertGreater(g.players.get(2)["coins"], coins2)
        top = g.events.participants(eid)[0]["user_id"]
        sealed = g.db.one("SELECT * FROM ghost_instances WHERE id=?", (ev["ghost_instance_id"],))
        self.assertEqual((sealed["state"], sealed["owner_id"]), ("sealed", top))
        self.assertEqual(g.inv.count(top, "vat_chua_vang"), 1)
        self.assertEqual(g.world._row("khu_dan_cu")["danger_mod"], 0)
        self.assertTrue(any(a["kind"] == "success" for a in g.events.drain_announcements()))

    def test_team_bonus_only_from_three_participants(self):
        g = self.g
        eid = g.events.start_event("khan_cap", "khu_dan_cu")
        r1 = g.events.participate(1, eid, "dieu_tra")
        self.assertIn("+2 đóng góp", r1["lines"][0])                     # đi lẻ: không thưởng
        g.clock.advance(25)
        r2 = g.events.participate(2, eid, "dieu_tra")
        self.assertIn("+2 đóng góp", r2["lines"][0])                     # mới 2 người
        r3 = g.events.participate(3, eid, "dieu_tra")
        self.assertIn("+3 đóng góp", r3["lines"][0])                     # đủ 3: +1 yểm trợ
        self.assertIn("Đội hình 3 người", r3["lines"][0])
        self.assertEqual(g.events.get(eid)["progress"], 7)
        self.assertEqual({r["user_id"]: r["contribution"] for r in g.events.participants(eid)}, {1: 2, 2: 2, 3: 3})

    def test_event_failure_locks_location_and_hurts_participants(self):
        g = self.g
        eid = g.events.start_event("khan_cap", "khu_dan_cu")
        g.events.participate(1, eid, "dieu_tra")
        hp = g.players.get(1)["hp"]
        g.clock.advance(EVENT_DEFS["khan_cap"]["duration"] + 5)
        g.events.tick()
        self.assertEqual(g.events.get(eid)["state"], "failed")
        self.assertTrue(g.world.lock_info("khu_dan_cu")[0])
        self.assertLess(g.players.get(1)["hp"], hp)
        self.assertGreaterEqual(g.world.unrest(), 5)
        with self.assertRaises(GameError):
            g.explore.explore(2, "tham_do")

    def test_ap_che_requires_resource_and_uses_ghost_or_talisman(self):
        g = self.g
        eid = g.events.start_event("khan_cap", "khu_dan_cu")
        with self.assertRaises(GameError):
            g.events.participate(1, eid, "ap_che")
        g.inv.add(1, "bua_ap_che", 1)
        g.events.participate(1, eid, "ap_che")
        self.assertEqual(g.inv.count(1, "bua_ap_che"), 0)

    def test_global_event_modifies_world(self):
        g = self.g
        base = g.world.effective_danger("khu_dan_cu")
        g.events.start_event("dem_trang_mau")
        self.assertEqual(g.world.effective_danger("khu_dan_cu"), base + 1)
        self.assertGreater(g.world.modifiers()["clue_bonus"], 0)
        g.clock.advance(EVENT_DEFS["dem_trang_mau"]["duration"] + 1)
        g.events.tick()
        self.assertEqual(g.world.effective_danger("khu_dan_cu"), base)

    def test_timed_event_unlocks_station_and_punishes_stragglers(self):
        g = self.g
        g.db.run("UPDATE players SET location_id='thanh_pho',level=5 WHERE user_id=1")
        g.events.start_event("chuyen_tau_cuoi")
        g.world.travel(1, "ga_cuoi")
        san = g.players.get(1)["sanity"]
        g.clock.advance(EVENT_DEFS["chuyen_tau_cuoi"]["duration"] + 1)
        g.events.tick()
        p = g.players.get(1)
        self.assertEqual(p["location_id"], "thanh_pho")
        self.assertLess(p["sanity"], san)
        with self.assertRaises(GameError):
            g.world.travel(1, "ga_cuoi")

    def test_tick_spawns_events_with_forced_rng(self):
        g = self.g
        g.rng.forced = 0.0
        g.events.tick()
        g.rng.forced = None
        kinds = {e["kind"] for e in g.events.active()}
        self.assertTrue({"contrib", "global", "timed"} <= kinds)
        self.assertLessEqual(sum(1 for e in g.events.active() if e["kind"] == "contrib"), 2)

    def test_danger_mod_decays(self):
        g = self.g
        g.world.add_danger_mod("khu_dan_cu", 2)
        g.events.tick()
        g.clock.advance(6 * 3600 + 5)
        g.events.tick()
        self.assertEqual(g.world._row("khu_dan_cu")["danger_mod"], 1)

    def test_story_branches_endings_and_world_impact(self):
        g = self.g
        g.db.run("UPDATE players SET location_id='thanh_pho' WHERE user_id=1")
        g.inv.add(1, "thu_linh_di", 3)
        lines = g.inv.use(1, "thu_linh_di")
        self.assertIn("Bức Thư", lines[0])
        with self.assertRaises(GameError):
            g.inv.use(1, "thu_linh_di")           # đang đọc dở
        v = g.events.story_view(1)
        self.assertEqual([c["id"] for c in v["choices"]], ["doc_tiep", "dot_thu"])
        g.events.story_choose(1, "doc_tiep")
        v = g.events.story_view(1)
        flags = {c["id"]: c["ok"] for c in v["choices"]}
        # Cảnh Sát khởi đầu có Đèn Dầu Cũ nên được chọn "viết thư"; hai lối kia bị khóa vì sai nơi / chưa vào Tổng Bộ
        self.assertEqual(flags, {"mo_cua": False, "bao_tong_bo": False, "viet_thu": True})
        with self.assertRaises(GameError):
            g.events.story_choose(1, "mo_cua")
        g.db.run("UPDATE players SET location_id='khu_dan_cu' WHERE user_id=1")
        res = g.events.story_choose(1, "mo_cua")
        self.assertTrue(res["ended"])
        self.assertEqual(g.world._row("khu_dan_cu")["danger_mod"], 1)
        self.assertIsNotNone(g.db.one("SELECT 1 FROM ghost_instances WHERE state='free' AND ghost_id='quy_mon'"))
        self.assertIn(1, g.ghosts.clues_known(1, "quy_mon"))
        # kết cục khác: báo Tổng Bộ -> phong tỏa chủ động + giảm bất ổn
        g.db.run("UPDATE players SET location_id='thanh_pho' WHERE user_id=1")
        g.orgs.join(1)
        g.inv.use(1, "thu_linh_di")
        g.events.story_choose(1, "doc_tiep")
        g.events.story_choose(1, "bao_tong_bo")
        self.assertTrue(g.world.lock_info("khu_dan_cu")[0])
        endings = {r["ending_id"] for r in g.db.all("SELECT ending_id FROM story_endings WHERE user_id=1")}
        self.assertEqual(endings, {"mo_cua", "bao_tong_bo"})

    def test_resurrection_chain_event_to_fail_to_lock(self):
        """Liên kết hệ thống: Ngự Quỷ Giả -> phục tô -> sự kiện -> phong tỏa -> thế giới."""
        g = self.g
        g.rng.forced = 0.0
        inst = g.ghosts.spawn("quy_thu", "khu_dan_cu")
        g.ghosts.bind(1, inst)
        g.rng.forced = None
        g.db.run("UPDATE ghost_instances SET resurrection=99.5 WHERE id=?", (inst,))
        g.clock.advance(3600)
        g.players.refresh(1)
        ev = g.db.one("SELECT * FROM world_events WHERE def_id='phuc_to'")
        self.assertIsNotNone(ev)
        g.clock.advance(EVENT_DEFS["phuc_to"]["duration"] + 1)
        g.events.tick()
        self.assertTrue(g.world.lock_info("khu_dan_cu")[0])
        self.assertEqual(g.ghosts.get(inst)["state"], "free")


if __name__ == "__main__":
    unittest.main()

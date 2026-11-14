import json
import unittest

from core.errors import GameError
from data.ghosts import GHOSTS
from engine.mechanics import MECHANICS
from tests.helpers import make_game, mkplayer

HAS_NONE = lambda i: False  # noqa: E731


def run_until_end(mech, st, rng, picker, p=None, known=frozenset(), has=HAS_NONE, limit=40):
    p = p or {"sanity": 100, "hp": 100}
    for _ in range(limit):
        scene = mech.scene(st, set(known), has)
        step = mech.act(st, picker(st, scene), rng, p)
        if step.outcome != "continue":
            return step.outcome
    raise AssertionError("không kết thúc")


class MechanicTests(unittest.TestCase):
    def setUp(self):
        self.g = make_game(3)
        self.rng = self.g.rng

    def test_every_ghost_has_distinct_mechanic_and_complete_data(self):
        self.assertEqual(len({g["mechanic"] for g in GHOSTS.values()}), len(GHOSTS))
        need = {"name", "origin", "rank", "kill_rule", "powers", "range", "domain", "counter", "suppress_text",
                "clues", "resurrect_text", "rate", "polarity", "suppresses", "conflicts", "awaken"}
        for gid, g in GHOSTS.items():
            self.assertFalse(need - set(g), gid)
            self.assertEqual(len(g["clues"]), 3)
            self.assertIn(g["mechanic"], MECHANICS)
        # vòng khắc chế khép kín: mỗi quỷ (trừ Quỷ Vực) bị đúng một quỷ khác khắc chế
        from data.ghosts import suppressors_of
        for gid in GHOSTS:
            self.assertEqual(len(suppressors_of(gid)), 0 if gid == "quy_vuc" else 1, gid)

    def test_quy_thu_stillness_wins_and_struggle_kills(self):
        m = MECHANICS["quy_thu"]
        self.assertEqual(run_until_end(m, m.start(self.rng), self.rng, lambda s, sc: "dung_yen"), "survive")
        self.assertEqual(run_until_end(m, m.start(self.rng), self.rng, lambda s, sc: "giay_dua"), "death")

    def test_quy_anh_clue_makes_it_safe_without_clue_is_risky(self):
        m = MECHANICS["quy_anh"]

        def safe(st, sc):
            return next(o.id for o, l in zip(sc.options, st["spots"]) if l != 1)
        for _ in range(20):
            self.assertEqual(run_until_end(m, m.start(self.rng), self.rng, safe), "survive")
        deadly = lambda st, sc: next(o.id for o, l in zip(sc.options, st["spots"]) if l == 1)  # noqa: E731
        self.assertEqual(run_until_end(m, m.start(self.rng), self.rng, deadly), "death")
        st = m.start(self.rng)
        txt = " ".join(o.desc for o in m.scene(st, {0}, HAS_NONE).options)
        self.assertIn("nơi nó chờ", txt)
        txt = " ".join(o.desc for o in m.scene(st, set(), HAS_NONE).options)
        self.assertNotIn("nơi nó chờ", txt)

    def test_quy_nhan_alternating_gaze(self):
        m = MECHANICS["quy_nhan"]
        seq = iter(["lui", "lui", "nham_mat", "lui", "lui"])
        self.assertEqual(run_until_end(m, m.start(self.rng), self.rng, lambda s, sc: next(seq)), "survive")
        self.assertEqual(run_until_end(m, m.start(self.rng), self.rng, lambda s, sc: "nhin"), "death")
        self.assertEqual(run_until_end(m, m.start(self.rng), self.rng, lambda s, sc: "nham_mat"), "death")

    def test_quy_quan_tai_lid_items_and_low_sanity(self):
        m = MECHANICS["quy_quan_tai"]
        self.assertEqual(run_until_end(m, m.start(self.rng), self.rng, lambda s, sc: "dong_nap"), "survive")
        self.assertEqual(run_until_end(m, m.start(self.rng), self.rng, lambda s, sc: "dong_nap",
                                       p={"sanity": 5, "hp": 50}), "death")
        self.assertEqual(run_until_end(m, m.start(self.rng), self.rng, lambda s, sc: "nam_vao"), "death")
        step = m.act(m.start(self.rng), "dong_dinh", self.rng, {"sanity": 50})
        self.assertEqual((step.outcome, step.bind_bonus), ("survive", 0.3))

    def test_quy_mon_parity_rule(self):
        m = MECHANICS["quy_mon"]

        def right(st, sc):
            return "im_lang" if st["knocks"] % 2 else "mo_cua"

        def wrong(st, sc):
            return "mo_cua" if st["knocks"] % 2 else "im_lang"
        for _ in range(15):
            self.assertEqual(run_until_end(m, m.start(self.rng), self.rng, right), "survive")
        outcomes = {run_until_end(m, m.start(self.rng), self.rng, wrong) for _ in range(15)}
        self.assertIn("death", outcomes)

    def test_quy_vuc_anchor_search_and_air_limit(self):
        m = MECHANICS["quy_vuc"]
        st = m.start(self.rng)
        self.assertFalse(m.can_flee)
        self.assertEqual(m.act(st, f"pha_neo_{st['anchor']}", self.rng, {"sanity": 50}).outcome, "survive")
        st = m.start(self.rng)
        wrong = (st["anchor"] + 1) % 4
        self.assertEqual(run_until_end(m, st, self.rng, lambda s, sc: f"pha_neo_{wrong}"), "death")
        st = m.start(self.rng)
        self.assertEqual(run_until_end(m, st, self.rng, lambda s, sc: "tham_do_0"), "death")

    def test_shield_negates_one_mistake_each_mechanic(self):
        st = MECHANICS["quy_thu"].start(self.rng)
        st["shield"] = 1
        step = MECHANICS["quy_thu"].act(st, "giay_dua", self.rng, {})
        self.assertEqual(st["grip"], 0)
        self.assertEqual(step.dmg, {})


class GhostSystemTests(unittest.TestCase):
    def setUp(self):
        self.g = make_game(5)
        mkplayer(self.g, loc="khu_dan_cu", level=1)

    def bind(self, ghost_id, uid=1):
        inst = self.g.ghosts.spawn(ghost_id, self.g.players.get(uid)["location_id"])
        self.g.rng.forced = 0.0
        res = self.g.ghosts.bind(uid, inst)
        self.g.rng.forced = None
        self.assertTrue(res["success"])
        return inst

    def test_bind_makes_summoner_and_blocks_duplicate(self):
        inst = self.bind("quy_mon")
        p = self.g.players.get(1)
        self.assertEqual(p["is_summoner"], 1)
        self.assertEqual(self.g.ghosts.get(inst)["state"], "bound")
        again = self.g.ghosts.spawn("quy_mon", "khu_dan_cu")
        with self.assertRaises(GameError):
            self.g.ghosts.bind(1, again)

    def test_bind_chance_rewards_clues_and_suppressor(self):
        g = self.g
        inst = g.ghosts.get(g.ghosts.spawn("quy_nhan", "khu_dan_cu"))
        base = g.ghosts.bind_chance(1, inst)
        for i in range(3):
            g.ghosts.add_clue(1, "quy_nhan", i)
        with_clues = g.ghosts.bind_chance(1, inst)
        self.assertGreater(with_clues, base)
        self.bind("quy_anh")  # Quỷ Ảnh khắc chế Quỷ Nhãn
        self.assertGreater(g.ghosts.bind_chance(1, inst), with_clues)

    def test_resurrection_over_time_creates_world_event_and_loss_of_control(self):
        g = self.g
        inst = self.bind("quy_thu")
        g.clock.advance(3600 * 20)   # 2.0/giờ -> 40%
        g.players.refresh(1)
        self.assertAlmostEqual(g.ghosts.get(inst)["resurrection"], 50.0, delta=1)
        g.clock.advance(3600 * 40)
        p = g.players.refresh(1)
        self.assertEqual(g.ghosts.get(inst)["state"], "free")
        self.assertEqual(p["status"], "mat_kiem_soat")
        ev = g.db.one("SELECT * FROM world_events WHERE def_id='phuc_to'")
        self.assertEqual((ev["location_id"], ev["ghost_instance_id"]), ("khu_dan_cu", inst))
        self.assertGreater(g.world.unrest(), 0)

    def test_suppressor_halves_rate_and_imbalance_raises_it(self):
        g = self.g
        a = self.bind("quy_thu")           # +2
        base = g.ghosts.rate_for(g.ghosts.get(a), g.ghosts.owned(1), g.players.get(1))
        self.assertAlmostEqual(base, 2.0)
        g.db.run("UPDATE players SET level=24 WHERE user_id=1")
        b = self.bind("quy_quan_tai")      # Quan Tài khắc chế Thủ (x0.5), nhưng xung đột? (Thủ-Môn, Ảnh-Quan Tài)
        owned = g.ghosts.owned(1)
        self.assertAlmostEqual(g.ghosts.rate_for(g.ghosts.get(a), owned, g.players.get(1)), 1.0)
        self.bind("quy_mon")               # +1 -> cân bằng = 2 -1 +1 = 2, xung đột Thủ-Môn x1.4
        owned = g.ghosts.owned(1)
        self.assertEqual(g.ghosts.balance(1), 2)
        self.assertGreater(g.ghosts.rate_for(g.ghosts.get(a), owned, g.players.get(1)), 1.0)

    def test_over_slot_limit_adds_corruption(self):
        g = self.g
        self.bind("quy_thu")
        before = g.players.get(1)["corruption"]
        self.bind("quy_anh")   # level 1 => 1 khe, đang giữ 1 => vượt
        self.assertGreaterEqual(g.players.get(1)["corruption"], before + 10)

    def test_use_power_effects_and_awakening(self):
        g = self.g
        inst = self.bind("quy_thu")
        lines = g.ghosts.use_power(1, inst, "nam_lay")
        self.assertTrue(lines)
        self.assertEqual(g.players.buff(1, "loot"), 2)
        for _ in range(5):
            g.ghosts.reduce_resurrection(inst, 100)
            g.ghosts.use_power(1, inst, "nam_lay")
        self.assertEqual(g.ghosts.get(inst)["awakened"], 1)
        self.assertEqual(g.progress.stat(1, "awakens"), 1)
        self.assertTrue(any("Thức tỉnh" in n for n in g.drain_notices(1)))

    def test_power_that_overheats_triggers_resurrection(self):
        g = self.g
        inst = self.bind("quy_vuc")
        g.db.run("UPDATE ghost_instances SET resurrection=90 WHERE id=?", (inst,))
        lines = g.ghosts.use_power(1, inst, "mo_vuc")
        self.assertIn("phục tô", lines[0])
        self.assertEqual(g.ghosts.get(inst)["state"], "free")

    def test_suppress_power_needs_other_ghost(self):
        g = self.g
        g.db.run("UPDATE players SET level=24 WHERE user_id=1")
        a, b = self.bind("quy_quan_tai"), self.bind("quy_thu")
        g.db.run("UPDATE ghost_instances SET resurrection=70 WHERE id=?", (b,))
        with self.assertRaises(GameError):
            g.ghosts.use_power(1, a, "dong_nap")
        g.ghosts.use_power(1, a, "dong_nap", target_inst_id=b)
        self.assertAlmostEqual(g.ghosts.get(b)["resurrection"], 35, delta=1)

    def test_seal_and_handover_flow(self):
        g = self.g
        inst = g.ghosts.spawn("quy_mon", "khu_dan_cu")
        with self.assertRaises(GameError):
            g.ghosts.seal(1, inst)  # thiếu Vật Chứa Vàng
        g.inv.add(1, "vat_chua_vang", 1)
        res = g.ghosts.seal(1, inst)
        self.assertEqual(res["ghost"], "quy_mon")
        self.assertEqual(g.ghosts.get(inst)["state"], "sealed")
        with self.assertRaises(GameError):
            g.ghosts.hand_over(1, inst)  # chưa vào Tổng Bộ
        g.orgs.join(1) if False else None
        g.players.adjust(1, coins=0)
        g.db.run("UPDATE players SET location_id='thanh_pho' WHERE user_id=1")
        g.orgs.join(1)
        coins = g.players.get(1)["coins"]
        out = g.ghosts.hand_over(1, inst)
        self.assertEqual(g.players.get(1)["coins"], coins + out["coins"])
        with self.assertRaises(GameError):
            g.ghosts.get(inst)

    def test_codex_reveals_by_knowledge(self):
        g = self.g
        c = g.ghosts.codex(1, "quy_nhan")
        self.assertEqual(c["fields"], {"name": "???"})
        g.ghosts.add_clue(1, "quy_nhan", 0)
        f = g.ghosts.codex(1, "quy_nhan")["fields"]
        self.assertIn("kill_rule", f)
        self.assertNotIn("counter", f)
        for i in (1, 2):
            g.ghosts.add_clue(1, "quy_nhan", i)
        self.assertIn("awaken", g.ghosts.codex(1, "quy_nhan")["fields"])


class RescueTests(unittest.TestCase):
    def test_teammate_talisman_ends_loss_of_control_and_cools_ghost(self):
        g = make_game(9)
        mkplayer(g, 1, name="Cuu Ho", loc="khu_dan_cu")
        mkplayer(g, 2, name="Bi Nan", loc="khu_dan_cu")
        inst = g.ghosts.spawn("quy_mon", "khu_dan_cu")
        g.rng.forced = 0.0
        g.ghosts.bind(2, inst)
        g.rng.forced = None
        g.players.adjust(2, sanity=-999)                     # sụp đổ: ghost +25
        self.assertEqual(g.players.get(2)["status"], "mat_kiem_soat")
        before = g.ghosts.get(inst)["resurrection"]
        with self.assertRaises(GameError):
            g.ghosts.rescue(1, 2)                            # thiếu bùa
        g.inv.add(1, "bua_ap_che", 1)
        with self.assertRaises(GameError):
            g.ghosts.rescue(1, 1)
        g.ghosts.rescue(1, 2)
        self.assertEqual(g.players.get(2)["status"], "binh_thuong")
        self.assertLess(g.ghosts.get(inst)["resurrection"], before)
        self.assertEqual(g.inv.count(1, "bua_ap_che"), 0)
        with self.assertRaises(GameError):
            g.inv.add(1, "bua_ap_che", 1) or g.ghosts.rescue(1, 2)   # người này đã ổn


class EncounterFlowTests(unittest.TestCase):
    def setUp(self):
        self.g = make_game(7)
        mkplayer(self.g, loc="khu_dan_cu", sanity=100)

    def state(self):
        return json.loads(self.g.db.one("SELECT state_json FROM encounters WHERE user_id=1")["state_json"])

    def test_full_quy_mon_flow_survive_then_bind(self):
        g = self.g
        info = g.enc.start(1, "quy_mon")
        self.assertTrue(info["started"])
        with self.assertRaises(GameError):
            g.explore.explore(1, "tham_do")  # đang đối mặt
        for _ in range(4):
            odd = self.state()["knocks"] % 2
            res = g.enc.act(1, "im_lang" if odd else "mo_cua")
            self.assertIn(res["status"], ("continue", "cleared"))
        self.assertEqual(g.enc.view(1)["phase"], "cleared")
        with self.assertRaises(GameError):
            g.enc.act(1, "im_lang")
        g.rng.forced = 0.0
        res = g.enc.bind(1)
        g.rng.forced = None
        self.assertTrue(res["success"])
        self.assertIsNone(g.enc.active(1))
        self.assertEqual(len(g.ghosts.owned(1)), 1)
        self.assertGreater(g.progress.stat(1, "survives"), 0)

    def test_death_in_encounter_respawns_in_hub(self):
        g = self.g
        g.enc.start(1, "quy_nhan")
        for _ in range(3):
            res = g.enc.act(1, "nhin")
            if res["status"] == "death":
                break
        self.assertEqual(res["status"], "death")
        p = g.players.get(1)
        self.assertEqual(p["location_id"], "thanh_pho")
        self.assertIsNone(g.enc.active(1))
        self.assertEqual(g.progress.stat(1, "deaths"), 1)
        self.assertEqual(g.db.one("SELECT 1 FROM player_achievements WHERE ach_id='chet_mot_lan'") is not None, True)

    def test_item_options_require_inventory_and_are_consumed(self):
        g = self.g
        g.enc.start(1, "quy_thu")
        ids = [o.id for o in g.enc.view(1)["scene"].options]
        self.assertNotIn("dua_vat", ids)
        g.inv.add(1, "hinh_nhan", 1)
        ids = [o.id for o in g.enc.view(1)["scene"].options]
        self.assertIn("dua_vat", ids)
        res = g.enc.act(1, "dua_vat")
        self.assertEqual(res["status"], "cleared")
        self.assertEqual(g.inv.count(1, "hinh_nhan"), 0)

    def test_clues_reveal_hints_in_view(self):
        g = self.g
        g.enc.start(1, "quy_anh")
        self.assertEqual(g.enc.view(1)["hints"], [])
        g.ghosts.add_clue(1, "quy_anh", 0)
        self.assertEqual(len(g.enc.view(1)["hints"]), 1)

    def test_flee_and_quy_vuc_cannot_flee(self):
        g = self.g
        g.enc.start(1, "quy_mon")
        g.rng.forced = 0.0
        self.assertEqual(g.enc.flee(1)["status"], "escaped")
        g.rng.forced = None
        self.assertIsNone(g.enc.active(1))
        g.db.run("UPDATE players SET sanity=100,hp=100 WHERE user_id=1")
        g.enc.start(1, "quy_vuc")
        res = g.enc.flee(1)
        self.assertIn("Không có lối ra", res["lines"][0])
        self.assertIsNotNone(g.enc.active(1))

    def test_power_in_encounter_shield_and_escape_and_reveal(self):
        g = self.g
        g.db.run("UPDATE players SET level=24 WHERE user_id=1")
        mon = g.ghosts.spawn("quy_mon", "khu_dan_cu")
        anh = g.ghosts.spawn("quy_anh", "khu_dan_cu")
        g.rng.forced = 0.0
        g.ghosts.bind(1, mon)
        g.ghosts.bind(1, anh)
        g.rng.forced = None
        g.enc.start(1, "quy_thu")
        self.assertEqual(g.enc.use_power(1, anh, "an_than")["status"], "continue")
        self.assertEqual(self.state()["shield"], 1)
        res = g.enc.use_power(1, mon, "mo_cua")
        self.assertEqual(res["status"], "escaped")
        self.assertIsNone(g.enc.active(1))


if __name__ == "__main__":
    unittest.main()

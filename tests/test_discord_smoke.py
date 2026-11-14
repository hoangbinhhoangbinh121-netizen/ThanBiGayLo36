"""Kiểm thử khói lớp Discord bằng bộ giả lập (tests/fake_discord.py).

Chạy THẬT: bot.setup_hook, nạp 8 Cog, đồng bộ emoji (API giả), kiểm tra ràng buộc lệnh của Discord, rồi cho một
người chơi đi trọn hành trình qua các lệnh/menu/nút. Mọi Embed và thành phần UI đều bị ép đúng giới hạn thật.
Không thay thế kiểm thử với Discord thật (xem TEST_REPORT.md).
"""
import random
import tempfile
import types
import unittest
from pathlib import Path

from tests import fake_discord
from tests.helpers import FakeClock, StubRng

fake_discord.install()

import bot as botmod  # noqa: E402
from core.config import Config  # noqa: E402
from core.cooldown import Limiter  # noqa: E402
from core.errors import GameError  # noqa: E402
from core.guards import NotAdmin, RateLimited  # noqa: E402

Choice = fake_discord.Choice


class _Msg:
    def __init__(self, embeds, view):
        self.embeds, self.view = embeds, view


class _Resp:
    def __init__(self, itx):
        self.itx, self.done = itx, False

    def is_done(self):
        return self.done

    def _record(self, kind, embed=None, embeds=None, view=None, ephemeral=False, content=None):
        for e in ([embed] if embed else []) + list(embeds or []):
            e.validate()
            _no_truncation(e)
        self.itx.sent.append({"kind": kind, "embed": embed or (embeds[0] if embeds else None), "content": content,
                              "ephemeral": ephemeral})
        self.done = True

    async def send_message(self, content=None, *, embed=None, embeds=None, view=None, ephemeral=False, **kw):
        assert not self.done, "Phản hồi lần hai trên cùng một interaction (phải dùng followup)"
        assert view is not False
        self._record("send", embed, embeds, view, ephemeral, content)
        self.itx.message = _Msg([embed] if embed else list(embeds or []), view)

    async def edit_message(self, *, embed=None, embeds=None, view=fake_discord.MISSING, content=None, **kw):
        assert not self.done, "Phản hồi lần hai trên cùng một interaction"
        self._record("edit", embed, embeds, None, False, content)
        prev = self.itx.message
        self.itx.message = _Msg([embed] if embed else (prev.embeds if prev else []),
                                prev.view if view is fake_discord.MISSING else view)

    async def defer(self, ephemeral=False):
        assert not self.done
        self.done = True


class _Follow:
    def __init__(self, itx):
        self.itx = itx

    async def send(self, *, content=None, embed=None, embeds=None, view=None, ephemeral=False, **kw):
        assert self.itx.response.done, "followup trước khi phản hồi"
        for e in ([embed] if embed else []) + list(embeds or []):
            e.validate()
            _no_truncation(e)
        self.itx.sent.append({"kind": "followup", "embed": embed or (embeds[0] if embeds else None), "content": content,
                              "ephemeral": ephemeral})


class FakeItx:
    def __init__(self, bot, uid, name="Người Chơi", message=None, admin=False, values=None):
        self.client = bot
        self.user = types.SimpleNamespace(id=uid, display_name=name, mention=f"<@{uid}>",
                                          guild_permissions=types.SimpleNamespace(administrator=admin))
        self.message, self.data, self.sent = message, ({"values": values} if values else {}), []
        self.response, self.followup, self.command = _Resp(self), _Follow(self), None

    async def original_response(self):
        return self.message


def _no_truncation(e):
    """cut() trong render.py cắt âm thầm; coi mọi nội dung bị cắt (kết thúc bằng …) là lỗi bố cục."""
    assert not (e.description or "").endswith("…"), f"description bị cắt: {e.title}"
    for n, v, _ in e.fields:
        assert not v.endswith("…"), f"field {n!r} của {e.title!r} bị cắt ({len(v)} ký tự)"


def user(uid, name="Ai Đó"):
    return types.SimpleNamespace(id=uid, mention=f"<@{uid}>", display_name=name)


class SmokeBase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cfg = Config(db_path=str(Path(self.tmp.name) / "t.db"), backup_dir=str(Path(self.tmp.name) / "bk"),
                     owner_ids=[999], auto_upload_emoji=True, backup_keep=3, emoji_upload_delay=0.0)
        self.bot = botmod.TBPTBot(cfg)
        self.mono = [1000.0]                                   # đồng hồ chống spam giả, trôi theo từng lệnh
        self.bot.limiter = Limiter(now=lambda: self.mono[0])
        await self.bot.setup_hook()
        self.g = self.bot.game
        self.g.clock, self.g.rng = FakeClock(), StubRng(5)
        self.rnd = random.Random(7)

    async def asyncTearDown(self):
        await self.bot.close()
        self.tmp.cleanup()

    # ---- tiện ích ---------------------------------------------------------------
    def find(self, cog_name, *path):
        cog = self.bot.get_cog(cog_name)
        obj = getattr(type(cog), path[0]) if path[0] in vars(type(cog)) else next(
            i for i in type(cog).__app_items__ if i.name == path[0])
        if len(path) == 2:
            obj = next(c for c in obj.commands if c.name == path[1])
        return cog, obj

    async def invoke(self, cog_name, path, uid=100, admin=False, itx=None, tick=10, **kw):
        path = (path,) if isinstance(path, str) else path
        self.mono[0] += tick
        cog, cmd = self.find(cog_name, *path)
        itx = itx or FakeItx(self.bot, uid, admin=admin)
        try:
            for chk in cmd.checks:
                await chk(itx)
            await cmd.callback(cog, itx, **kw)
        except fake_discord.AppCommandError as e:
            await self.bot.on_tree_error(itx, e)
            itx.error = e
        return itx

    async def press(self, view, child, itx_from, values=None, uid=None):
        itx = FakeItx(self.bot, uid or itx_from.user.id, message=itx_from.message, values=values)
        assert await view.interaction_check(itx), "interaction_check chặn nhầm chủ nhân"
        await child.callback(itx)
        return itx

    def last_embed(self, itx):
        return itx.sent[-1]["embed"]

    async def make_player(self, uid=100, name="Lâm Phong", origin="canh_sat"):
        itx = await self.invoke("CharacterCog", "tao", uid, ten=name)
        view = itx.message.view
        await self.press(view, view.children[0], itx, [origin])
        return self.g.players.get(uid)


class CommandTreeTests(SmokeBase):
    async def test_all_commands_register_and_satisfy_discord_constraints(self):
        names = {i.name for i in self.bot.tree.get_commands()}
        expected = {"tao_nhan_vat", "ho_so", "nghi_ngoi", "lich_su", "thanh_tuu", "bxh", "tro_giup", "ban_do", "dia_diem",
                    "di_chuyen", "kham_pha", "doi_mat", "quy", "ap_che_dong_doi", "kho_do", "dung_vat_pham", "cua_hang",
                    "mua", "ban", "giao_dich", "to_chuc", "su_kien", "nhiem_vu", "admin", "xoa_nhan_vat"}
        self.assertEqual(expected, names)
        subs = sum(len(i.commands) for i in self.bot.tree.get_commands() if hasattr(i, "commands"))
        print(f"\n[smoke] {len(names)} lệnh gốc, {subs} lệnh con")
        self.assertLessEqual(len(names), 100)
        self.assertGreater(subs, 35)
        self.assertEqual(self.g.db.schema_version(), 5)

    async def test_emoji_sync_is_idempotent_and_used_in_ui(self):
        reg = self.bot.emoji_reg
        self.assertEqual(reg.uploaded(), 35)
        self.assertEqual(len(self.bot.app_emojis), 35)
        self.assertEqual(self.g.db.scalar("SELECT COUNT(*) FROM emoji_registry"), 35)
        created, total = await reg.sync(self.bot)
        self.assertEqual((created, total), (0, 35))
        self.assertTrue(self.bot.ui.e("ghost_quy_thu").startswith("<:ghost_quy_thu:"))
        bar = self.bot.ui.bar(5, 10, "hp")
        self.assertEqual(bar.count("<:bar_hp:"), 5)
        self.assertEqual(bar.count("<:bar_empty:"), 5)
        fresh = type(reg)(reg.dir)
        self.assertTrue(fresh.fmt("ghost_quy_thu"))        # dự phòng trước khi đồng bộ
        self.assertNotIn("<:", fresh.fmt("ghost_quy_thu"))


class JourneyTests(SmokeBase):
    async def test_new_player_full_first_hour(self):
        p = await self.make_player()
        self.assertEqual(p["name"], "Lâm Phong")
        self.g.db.run("UPDATE players SET coins=600 WHERE user_id=100")
        for path, kw in [("ho_so", {}), ("lich_su", {}), ("thanh_tuu", {}), ("tro_giup", {}), ("nghi_ngoi", {})]:
            itx = await self.invoke("CharacterCog", path, **kw)
            self.assertTrue(itx.sent, path)
        for kind in ("level", "reputation", "seals", "clues", "contribution"):
            await self.invoke("CharacterCog", "bxh", loai=Choice(name=kind, value=kind))
        for path in ("ban_do", "dia_diem"):
            await self.invoke("WorldCog", path)
        # cửa hàng, túi đồ, dùng đồ
        await self.invoke("ItemCog", "cua_hang")
        itx = await self.invoke("ItemCog", "mua", vat_pham=Choice(name="Băng", value="bang_gac"), so_luong=2)
        self.assertEqual(self.g.inv.count(100, "bang_gac"), 2)
        itx = await self.invoke("ItemCog", "kho_do")
        view = itx.message.view
        self.g.db.run("UPDATE players SET hp=40 WHERE user_id=100")
        await self.press(view, view.children[0], itx, ["bang_gac"])
        self.assertEqual(self.g.inv.count(100, "bang_gac"), 1)
        await self.invoke("ItemCog", "ban", vat_pham=Choice(name="Băng", value="bang_gac"), so_luong=1)
        # di chuyển
        itx = await self.invoke("WorldCog", "di_chuyen")
        view = itx.message.view
        await self.press(view, view.children[0], itx, ["khu_dan_cu"])
        self.assertEqual(self.g.players.get(100)["location_id"], "khu_dan_cu")

    async def play(self, uid, steps, loc="khu_dan_cu", level=6):
        """Chơi ngẫu nhiên qua nút bấm/menu thật của Cog; trả bộ đếm các màn đã đi qua."""
        await self.make_player(uid, f"Khách {uid}")
        self.g.db.run("UPDATE players SET location_id=?,level=? WHERE user_id=?", (loc, level, uid))
        seen = {"explore": 0, "encounter": 0, "cleared": 0, "final": 0, "power": 0}
        itx = await self.invoke("ExploreCog", "kham_pha", uid)
        for _ in range(steps):
            self.g.clock.advance(60)
            self.g.db.run("UPDATE players SET hp=max_hp,sanity=max_sanity,status='binh_thuong' WHERE user_id=? "
                          "AND NOT EXISTS (SELECT 1 FROM encounters WHERE user_id=?)", (uid, uid))
            view = itx.message.view if itx.message else None
            if view is None or view.stopped:
                if self.g.players.get(uid)["location_id"] == "thanh_pho":
                    self.g.db.run("UPDATE players SET location_id=? WHERE user_id=?", (loc, uid))
                seen["final"] += 1
                itx = await self.invoke("ExploreCog", "doi_mat" if self.g.enc.active(uid) else "kham_pha", uid)
                continue
            if type(view).__name__ == "ExploreView":
                seen["explore"] += 1
                itx = await self.press(view, view.children[self.rnd.randrange(3)], itx)
                continue
            seen["encounter"] += 1
            if type(view.children[0]).__name__ == "Select":
                roll = self.rnd.random()
                if len(view.children) == 3 and roll < 0.25:
                    seen["power"] += 1
                    itx = await self.press(view, view.children[1], itx, [view.children[1].options[0].value])
                elif roll < 0.35:
                    itx = await self.press(view, view.children[-1], itx)           # bỏ chạy
                else:
                    itx = await self.press(view, view.children[0], itx, [self.rnd.choice(view.children[0].options).value])
            else:
                seen["cleared"] += 1
                self.g.rng.forced = 0.0 if self.rnd.random() < 0.5 else None
                itx = await self.press(view, self.rnd.choice([c for c in view.children if not c.disabled]), itx)
                self.g.rng.forced = None
        return seen

    async def test_exploration_loop_through_buttons_and_encounter_menus(self):
        seen = await self.play(100, 120)
        print(f"\n[smoke] hành trình: {seen}")
        self.assertGreater(seen["explore"], 5)
        self.assertGreater(seen["encounter"], 3)
        self.assertGreater(self.g.progress.stat(100, "explores"), 10)

    async def test_fuzz_many_players_and_locations_never_crash(self):
        total = {"explore": 0, "encounter": 0, "cleared": 0, "final": 0, "power": 0}
        for i, loc in enumerate(["khu_dan_cu", "benh_vien", "truong_hoc", "nghia_trang", "lang_hoang"] * 3):
            self.g.rng, self.rnd = StubRng(100 + i), random.Random(100 + i)
            seen = await self.play(300 + i, 70, loc, level=8 if i % 2 else 3)
            for k, v in seen.items():
                total[k] += v
        print(f"[smoke] fuzz 15 người chơi: {total}")
        self.assertGreater(total["encounter"], 100)
        self.assertGreater(total["cleared"], 3)
        self.assertGreater(self.g.progress.stat(300, "explores"), 0)
        # DB vẫn nhất quán sau fuzz
        self.assertEqual(self.g.db.one("PRAGMA foreign_key_check"), None)
        self.assertEqual(self.g.db.one("PRAGMA integrity_check")[0], "ok")

    async def test_encounter_resume_solve_bind_and_ghost_commands(self):
        await self.make_player()
        g = self.g
        g.db.run("UPDATE players SET location_id='khu_dan_cu',level=24,sanity=100 WHERE user_id=100")
        await bot_start(g, 100, "quy_mon")
        itx = await self.invoke("ExploreCog", "doi_mat")
        for _ in range(8):
            view = itx.message.view
            if view is None or view.children[0].__class__.__name__ != "Select":
                break
            knocks = __import__("json").loads(g.db.one("SELECT state_json FROM encounters WHERE user_id=100")["state_json"])["knocks"]
            itx = await self.press(view, view.children[0], itx, ["im_lang" if knocks % 2 else "mo_cua"])
        view = itx.message.view
        names = [c.label for c in view.children]
        self.assertEqual(names, ["Khống chế", "Phong ấn", "Rời đi"])
        self.assertTrue(view.children[1].disabled)       # chưa có Vật Chứa Vàng
        g.rng.forced = 0.0
        itx = await self.press(view, view.children[0], itx)
        g.rng.forced = None
        self.assertEqual(len(g.ghosts.owned(100)), 1)
        self.assertIn("khống chế", itx.sent[0]["embed"].title)
        # lệnh Ngự Quỷ Giả
        itx = await self.invoke("GhostCog", ("quy", "danh_sach"))
        self.assertIn("Quỷ Môn", itx.sent[0]["embed"].description)
        for gid in ("quy_thu", "quy_anh", "quy_nhan", "quy_quan_tai", "quy_mon", "quy_vuc"):
            await self.invoke("GhostCog", ("quy", "thong_tin"), quy=Choice(name=gid, value=gid))
        itx = await self.invoke("GhostCog", ("quy", "nang_luc"))
        view = itx.message.view
        itx = await self.press(view, view.children[0], itx, [view.children[0].options[0].value])
        itx = await self.press(view, view.children[-1], itx)
        self.assertGreater(g.ghosts.owned(100)[0]["resurrection"], 10)
        g.inv.add(100, "bua_ap_che", 1)
        itx = await self.invoke("GhostCog", ("quy", "ap_che"))
        view = itx.message.view
        await self.press(view, view.children[0], itx, [view.children[0].options[0].value])
        self.assertEqual(g.inv.count(100, "bua_ap_che"), 0)
        # phong ấn rồi bàn giao cho Tổng Bộ
        g.db.run("UPDATE players SET location_id='thanh_pho' WHERE user_id=100")
        await self.invoke("OrgCog", ("to_chuc", "gia_nhap"))
        inst = g.ghosts.spawn("quy_anh", "thanh_pho")
        g.inv.add(100, "vat_chua_vang", 1)
        g.ghosts.seal(100, inst)
        itx = await self.invoke("GhostCog", ("quy", "ban_giao"))
        view = itx.message.view
        itx = await self.press(view, view.children[0], itx, [view.children[0].options[0].value])
        self.assertIn("Đã bàn giao", itx.sent[0]["embed"].title)

    async def test_trade_flow_between_two_players(self):
        await self.make_player(100, "Người Một")
        await self.make_player(200, "Người Hai")
        self.g.inv.add(100, "den_dau", 2)
        itx = await self.invoke("ItemCog", ("giao_dich", "moi"), nguoi=user(200), cho_vat_pham=Choice(name="Đèn", value="den_dau"),
                             cho_so_luong=2, cho_xu=0, doi_vat_pham=None, doi_so_luong=1, doi_xu=30)
        view = itx.message.view
        await self.press(view, view.children[1], itx, uid=100)          # chủ gửi thử hủy? (nút 1 = hủy) -> hợp lệ
        itx = await self.invoke("ItemCog", ("giao_dich", "moi"), nguoi=user(200), cho_vat_pham=Choice(name="Đèn", value="den_dau"),
                             cho_so_luong=2, cho_xu=0, doi_vat_pham=None, doi_so_luong=1, doi_xu=30)
        view = itx.message.view
        # người lạ không được bấm
        stranger = FakeItx(self.bot, 777, message=itx.message)
        self.assertFalse(await view.interaction_check(stranger))
        before = self.g.players.get(100)["coins"]
        await self.press(view, view.children[0], itx, uid=200)
        self.assertEqual(self.g.players.get(100)["coins"], before + 30)
        self.assertEqual(self.g.inv.count(200, "den_dau"), 3)
        itx = await self.invoke("ItemCog", ("giao_dich", "danh_sach"), uid=200)
        self.assertTrue(itx.sent)

    async def test_org_events_story_and_background_loops(self):
        await self.make_player(100, "Tổng Bộ Một")
        await self.make_player(200, "Thành Viên")
        g = self.g
        g.db.run("UPDATE players SET location_id='thanh_pho' WHERE user_id IN (100,200)")
        await self.invoke("AdminCog", ("admin", "bo_nhiem"), uid=999, admin=True, nguoi=user(100))
        await self.invoke("OrgCog", ("to_chuc", "gia_nhap"), uid=200)
        for path in ("thong_tin", "thanh_vien", "nhiem_vu"):
            await self.invoke("OrgCog", ("to_chuc", path))
        itx = await self.invoke("OrgCog", ("to_chuc", "giao_nhiem_vu"), loai=Choice(name="Khám phá", value="explore"), so_lan=2,
                             thuong=50, khu_vuc=None, giao_cho=None, dia_diem=None, quy=None, gio=24)
        mid = g.db.scalar("SELECT id FROM org_missions")
        await self.invoke("OrgCog", ("to_chuc", "nhan_nhiem_vu"), uid=200, ma=mid)
        await self.invoke("OrgCog", ("to_chuc", "bao_cao"), uid=200, noi_dung="Phát hiện tiếng gõ cửa bất thường lúc nửa đêm.")
        await self.invoke("OrgCog", ("to_chuc", "duyet_bao_cao"), ma=None, duyet=True)
        await self.invoke("OrgCog", ("to_chuc", "duyet_bao_cao"), ma=1, duyet=True)
        g.db.run("UPDATE players SET reputation=30 WHERE user_id=200")
        await self.invoke("OrgCog", ("to_chuc", "thang_chuc"), nguoi=user(200), cap=None, khu_vuc=None)
        self.assertEqual(g.orgs.member(200)["rank"], "doi_truong")
        await self.invoke("OrgCog", ("to_chuc", "giang_chuc"), nguoi=user(200))
        await self.invoke("OrgCog", ("to_chuc", "khu_vuc"), nguoi=user(200), khu_vuc=Choice(name="Ngoại Ô", value="ngoai_o"))
        await self.invoke("OrgCog", ("to_chuc", "nop_quy"), uid=200, so_tien=30)
        g.world.lock("khu_dan_cu", 3600, "thử")
        await self.invoke("OrgCog", ("to_chuc", "mo_phong_toa"), dia_diem=Choice(name="Khu", value="khu_dan_cu"))
        self.assertFalse(g.world.lock_info("khu_dan_cu")[0])
        await self.invoke("OrgCog", ("to_chuc", "loai"), nguoi=user(200))
        self.assertIsNone(g.orgs.member(200))
        # sự kiện + kênh thông báo + vòng nền
        class Chan:
            id, sent = 555, []
            async def send(self, *, embed):
                embed.validate()
                self.sent.append(embed)
        chan = Chan()
        self.bot._channels[555] = chan
        await self.invoke("AdminCog", ("admin", "kenh"), uid=999, admin=True, kenh=types.SimpleNamespace(id=555, mention="#t"))
        await self.invoke("AdminCog", ("admin", "su_kien"), uid=999, admin=True, loai=Choice(name="QXH", value="quy_xuat_hien"),
                       dia_diem=Choice(name="Khu", value="khu_dan_cu"))
        self.assertTrue(chan.sent)
        g.db.run("UPDATE players SET location_id='khu_dan_cu',sanity=100 WHERE user_id=100")
        await self.invoke("EventCog", ("su_kien", "danh_sach"))
        eid = g.db.scalar("SELECT id FROM world_events WHERE def_id='quy_xuat_hien'")
        itx = await self.invoke("EventCog", ("su_kien", "tham_gia"), ma=eid, hanh_dong=Choice(name="Điều tra", value="dieu_tra"))
        self.assertIn("đóng góp", itx.sent[0]["embed"].description)
        cog = self.bot.get_cog("EventCog")
        g.clock.advance(10000)
        await cog.tick()
        self.assertGreaterEqual(len(chan.sent), 2)
        await cog.backup()
        self.assertTrue(list(Path(self.bot.cfg.backup_dir).glob("tbpt-*.db")))
        # cốt truyện nhiều kết cục qua nút bấm
        g.db.run("UPDATE players SET location_id='thanh_pho' WHERE user_id=100")
        g.inv.add(100, "thu_linh_di", 1)
        await self.invoke("ItemCog", "dung", vat_pham=Choice(name="Thư", value="thu_linh_di"))
        itx = await self.invoke("EventCog", ("su_kien", "cau_chuyen"))
        view = itx.message.view
        itx = await self.press(view, view.children[0], itx)               # đọc tiếp
        view = itx.message.view
        self.assertEqual(len(view.children), 3)
        itx = await self.press(view, view.children[2], itx)               # viết thư trả lời (có Đèn Dầu)
        self.assertIn("kết cục", itx.sent[0]["embed"].title)
        # nhiệm vụ
        await self.invoke("EventCog", ("nhiem_vu", "nhan"), nhiem_vu=Choice(name="Điều Tra", value="q_dieu_tra"))
        await self.invoke("EventCog", ("nhiem_vu", "danh_sach"))

    async def test_embeds_at_maximum_content_fit_discord_limits(self):
        g = self.g
        await self.make_player(100, "Tên Dài Hai Mươi Bốn Kí")
        g.db.run("UPDATE players SET level=40,location_id='thanh_pho',coins=99999,reputation=500 WHERE user_id=100")
        for i, gid in enumerate(("quy_thu", "quy_anh", "quy_nhan", "quy_quan_tai")):
            inst = g.ghosts.spawn(gid, "thanh_pho")
            g.rng.forced = 0.0
            g.ghosts.bind(100, inst)
            g.rng.forced = None
            g.db.run("UPDATE ghost_instances SET awakened=1,resurrection=? WHERE id=?", (55 + i * 11, inst))
            for c in range(3):
                g.ghosts.add_clue(100, gid, c)
        for k in ("quy_vuc", "quy_mon"):
            g.ghosts.seal  # noqa: B018  (khô kho: chỉ để đủ Vật Chứa niêm phong)
            inst = g.ghosts.spawn(k, "thanh_pho")
            g.inv.add(100, "vat_chua_vang", 1)
            g.ghosts.seal(100, inst)
        for it in ("den_dau", "bang_gac", "thuoc_an_than", "bua_ap_che", "dinh_quan_tai", "hinh_nhan", "thu_linh_di",
                   "quan_tai_nho", "guong_nut"):
            g.inv.add(100, it, 12)
        g.orgs.join(100)
        for uid in range(500, 524):
            await self.make_player(uid, f"Thành Viên Số {uid}")
            g.orgs.join(uid)
        g.events.start_event("quy_xuat_hien", "benh_vien")
        g.events.start_event("khan_cap", "truong_hoc")
        g.events.start_event("dem_trang_mau")
        g.events.start_event("chuyen_tau_cuoi")
        for path, kw in [("CharacterCog", ("ho_so", {})), ("CharacterCog", ("thanh_tuu", {})),
                         ("ItemCog", ("kho_do", {})), ("WorldCog", ("ban_do", {})), ("WorldCog", ("di_chuyen", {}))]:
            itx = await self.invoke(path, kw[0], **kw[1])
            self.assertFalse(hasattr(itx, "error"), kw[0])
        for path in (("quy", "danh_sach"),):
            await self.invoke("GhostCog", path)
        for gid in ("quy_thu", "quy_vuc"):
            await self.invoke("GhostCog", ("quy", "thong_tin"), quy=Choice(name=gid, value=gid))
        await self.invoke("OrgCog", ("to_chuc", "thanh_vien"))
        await self.invoke("OrgCog", ("to_chuc", "thong_tin"))
        await self.invoke("EventCog", ("su_kien", "danh_sach"))
        await self.invoke("EventCog", ("nhiem_vu", "danh_sach"))
        itx = await self.invoke("GhostCog", ("quy", "nang_luc"))
        self.assertTrue(itx.message.view.children)

    async def test_delete_character_flow_and_archive_command(self):
        g = self.g
        await self.make_player(100, "Tên Cần Xóa")
        itx = await self.invoke("CharacterCog", "xoa_nhan_vat", xac_nhan="Sai Tên")
        self.assertIn("không khớp", itx.sent[0]["embed"].description)
        self.assertTrue(g.players.exists(100))
        itx = await self.invoke("CharacterCog", "xoa_nhan_vat", xac_nhan="Tên Cần Xóa")
        view = itx.message.view
        itx2 = await self.press(view, view.children[1], itx)                      # Hủy
        self.assertTrue(g.players.exists(100))
        itx = await self.invoke("CharacterCog", "xoa_nhan_vat", xac_nhan="Tên Cần Xóa")
        view = itx.message.view
        stranger = FakeItx(self.bot, 5, message=itx.message)
        self.assertFalse(await view.interaction_check(stranger))
        await self.press(view, view.children[0], itx)                             # Xóa vĩnh viễn
        self.assertFalse(g.players.exists(100))
        # hồ sơ linh dị qua lệnh
        await self.make_player(100, "Tổng Bộ Mới")
        g.orgs.appoint_head(100)
        g.db.run("UPDATE players SET location_id='thanh_pho' WHERE user_id=100")
        itx = await self.invoke("OrgCog", ("to_chuc", "ho_so_linh_di"))
        self.assertIn("trống", itx.sent[0]["embed"].description)
        inst = g.ghosts.spawn("quy_thu", "thanh_pho")
        g.inv.add(100, "vat_chua_vang", 1)
        g.ghosts.seal(100, inst)
        g.ghosts.hand_over(100, inst)
        itx = await self.invoke("OrgCog", ("to_chuc", "ho_so_linh_di"))
        self.assertIn("Quỷ Thủ", itx.sent[0]["embed"].description)
        itx = await self.invoke("OrgCog", ("to_chuc", "ho_so_linh_di"), quy=Choice(name="Quỷ Thủ", value="quy_thu"))
        self.assertIn("Hồ sơ", itx.sent[0]["embed"].title)
        itx = await self.invoke("OrgCog", ("to_chuc", "thong_tin"))
        self.assertTrue(any(f[0].startswith("Kho giam giữ") for f in itx.sent[0]["embed"].fields))
        # admin xóa
        await self.make_player(201, "Bị Admin Xóa")
        await self.invoke("AdminCog", ("admin", "xoa_nhan_vat"), uid=999, admin=True, nguoi=user(201))
        self.assertFalse(g.players.exists(201))

    async def test_emoji_sync_rejects_invalid_file_and_throttles(self):
        reg = self.bot.emoji_reg
        reg.delay = 0.01
        slept = []
        import asyncio as _a
        real = _a.sleep
        async def fake_sleep(s):
            slept.append(s)
            await real(0)
        import core.emoji as emod
        emod.asyncio.sleep, old = fake_sleep, emod.asyncio.sleep
        try:
            self.bot.app_emojis.clear()                              # như bot mới: Discord chưa có emoji nào
            created, total = await reg.sync(self.bot)
            self.assertEqual((created, total), (35, 35))
            self.assertEqual(len(slept), 35)                          # giãn cách sau mỗi lần tải
            self.bot.app_emojis.clear()
            bad = reg.dir / "giao_dien" / "ui_sinh_ton.png"
            keep = bad.read_bytes()
            bad.write_bytes(b"khong phai png")
            try:
                with self.assertRaises(ValueError):
                    await reg.sync(self.bot)
            finally:
                bad.write_bytes(keep)
        finally:
            emod.asyncio.sleep = old

    async def test_admin_permissions_and_rate_limit(self):
        await self.make_player()
        itx = await self.invoke("AdminCog", ("admin", "thong_ke"), uid=100, admin=False)
        self.assertIsInstance(itx.error, NotAdmin)
        self.assertIn("quản trị", itx.sent[0]["embed"].description)
        itx = await self.invoke("AdminCog", ("admin", "thong_ke"), uid=999, admin=True)
        self.assertIn("Người chơi", itx.sent[0]["embed"].description)
        for path in (("admin", "emoji"), ("admin", "sao_luu")):
            itx = await self.invoke("AdminCog", path, uid=999, admin=True)
            self.assertTrue(itx.sent)
        await self.invoke("AdminCog", ("admin", "tang"), uid=999, admin=True, nguoi=user(100),
                       vat_pham=Choice(name="Gương", value="guong_nut"), so_luong=2)
        self.assertEqual(self.g.inv.count(100, "guong_nut"), 2)
        await self.invoke("AdminCog", ("admin", "mo_khoa"), uid=999, admin=True, dia_diem=Choice(name="x", value="khu_dan_cu"))
        # chống spam: gọi liên tiếp một lệnh
        await self.invoke("CharacterCog", "ho_so", uid=100)
        itx = await self.invoke("CharacterCog", "ho_so", uid=100, tick=0.5)
        self.assertIsInstance(itx.error, RateLimited)
        itx = await self.invoke("CharacterCog", "ho_so", uid=100, tick=3)       # đủ giãn cách thì qua
        self.assertFalse(hasattr(itx, "error"))
        for _ in range(16):                                                     # bắn liên tục -> bị chặn tạm
            itx = await self.invoke("CharacterCog", "tro_giup", uid=100, tick=1.2)
        self.assertIsInstance(getattr(itx, "error", None), RateLimited)

    async def test_business_errors_show_friendly_embed_not_traceback(self):
        itx = await self.invoke("CharacterCog", "ho_so", uid=4242)       # chưa có nhân vật
        self.assertEqual(len(itx.sent), 1)
        self.assertTrue(itx.sent[0]["ephemeral"])
        self.assertIn("/tao_nhan_vat", itx.sent[0]["embed"].description)
        await self.make_player()
        itx = await self.invoke("ExploreCog", "kham_pha", uid=100)       # mới tạo: ở Khu Trung Tâm
        view = itx.message.view
        itx2 = await self.press(view, view.children[0], itx)
        self.assertIn("an toàn", itx2.sent[0]["embed"].description)


async def bot_start(g, uid, ghost_id):
    await g.db.call(g.enc.start, uid, ghost_id)


if __name__ == "__main__":
    unittest.main()

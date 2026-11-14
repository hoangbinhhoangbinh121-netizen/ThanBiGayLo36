"""Sự kiện thế giới, cốt truyện nhiều kết cục, nhiệm vụ, và nhịp nền (tick sự kiện + sao lưu định kỳ)."""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import tasks

from cogs.base import FAILED, GameCog, OwnedView
from core.guards import rate_limit
from data.basics import QUESTS
from data.events import CONTRIB_ACTIONS

log = logging.getLogger("tbpt.events")
ANN_STYLE = {"start": ("warn", "ui_nguy_hiem"), "success": ("good", "ui_thanh_cong"), "fail": ("bad", "ui_that_bai"),
             "expire": ("info", "ui_kham_pha")}


class StoryView(OwnedView):
    def __init__(self, cog, owner_id, v):
        super().__init__(owner_id, 900)
        self.cog = cog
        for c in v["choices"]:
            b = discord.ui.Button(label=c["label"][:80], disabled=not c["ok"], style=discord.ButtonStyle.primary
                                  if c["ok"] else discord.ButtonStyle.secondary)
            b.callback = self._make(c["id"])
            self.add_item(b)

    def _make(self, cid):
        async def cb(itx: discord.Interaction):
            r = await self.cog.call(itx, self.cog.g.events.story_choose, itx.user.id, cid)
            if r is FAILED:
                return
            self.stop()
            if r["ended"]:
                await itx.response.edit_message(embed=self.cog.ui.story_end("Bức Thư Từ Người Đã Chết", r["text"], r["lines"]), view=None)
                return await self.cog.flush(itx)
            v = await self.cog.call(itx, self.cog.g.events.story_view, itx.user.id)
            if v is not FAILED:
                await self.cog.edit(itx, StoryView(self.cog, itx.user.id, v), embed=self.cog.ui.story(v))
        return cb


class EventCog(GameCog):
    su_kien = app_commands.Group(name="su_kien", description="Sự kiện linh dị của thế giới")
    nhiem_vu = app_commands.Group(name="nhiem_vu", description="Bảng nhiệm vụ")

    # ---- vòng nền ----------------------------------------------------------------
    async def cog_load(self):
        self.tick.change_interval(seconds=self.bot.cfg.tick_seconds)
        self.backup.change_interval(hours=self.bot.cfg.backup_interval_hours)
        self.tick.start()
        self.backup.start()

    async def cog_unload(self):
        self.tick.cancel()
        self.backup.cancel()

    @tasks.loop(seconds=60)
    async def tick(self):
        try:
            anns = await self.bot.db.call(self.g.events.tick)
            anns += await self.bot.db.call(self.g.events.drain_announcements)
        except Exception:
            log.exception("tick sự kiện lỗi")
            return
        await self.post(anns)

    @tick.before_loop
    async def _wait1(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=6)
    async def backup(self):
        try:
            path = await self.bot.db.call(self.bot.db.backup, self.bot.cfg.backup_dir, self.bot.cfg.backup_keep)
            log.info("Đã sao lưu: %s", path)
        except Exception:
            log.exception("sao lưu lỗi")

    @backup.before_loop
    async def _wait2(self):
        await self.bot.wait_until_ready()

    async def post(self, anns):
        if not anns:
            return
        cid = await self.bot.db.call(self.g.db.scalar, "SELECT value FROM world_state WHERE key='announce_channel'")
        channel = self.bot.get_channel(int(cid)) if cid else None
        if not channel:
            return
        for a in anns:
            color, icon = ANN_STYLE[a["kind"]]
            try:
                await channel.send(embed=self.ui.embed(a["title"], a["text"] + ("\n\nDùng `/su_kien danh_sach` để xem chi tiết."
                                                                                if a["kind"] == "start" else ""), color, icon))
            except discord.HTTPException:
                log.warning("Không gửi được thông báo sự kiện")

    # ---- lệnh sự kiện ----------------------------------------------------------------
    @su_kien.command(name="danh_sach", description="Sự kiện đang diễn ra")
    @rate_limit(3)
    async def ds(self, itx: discord.Interaction):
        rows = await self.call(itx, self.g.events.active)
        if rows is not FAILED:
            await itx.response.send_message(embed=self.ui.events(rows, None))

    @su_kien.command(name="tham_gia", description="Đóng góp vào sự kiện tại địa điểm bạn đang đứng")
    @app_commands.choices(hanh_dong=[app_commands.Choice(name=a["name"], value=k) for k, a in CONTRIB_ACTIONS.items()])
    @app_commands.describe(ma="Mã sự kiện (xem /su_kien danh_sach)")
    @rate_limit(3)
    async def tham_gia(self, itx: discord.Interaction, ma: int, hanh_dong: app_commands.Choice[str]):
        r = await self.call(itx, self.g.events.participate, itx.user.id, ma, hanh_dong.value)
        if r is FAILED:
            return
        await itx.response.send_message(embed=self.ui.embed("Sự kiện", "\n".join(r["lines"]), "good" if r["done"] else "warn",
                                                            "ui_chien_dau"))
        await self.flush(itx)
        await self.post(await self.bot.db.call(self.g.events.drain_announcements))

    @su_kien.command(name="cau_chuyen", description="Tiếp tục câu chuyện nhiều kết cục đang đọc dở (từ Thư Linh Dị)")
    @rate_limit(3)
    async def cau_chuyen(self, itx: discord.Interaction):
        v = await self.call(itx, self.g.events.story_view, itx.user.id)
        if v is FAILED:
            return
        view = StoryView(self, itx.user.id, v)
        await itx.response.send_message(embed=self.ui.story(v), view=view, ephemeral=True)
        view.message = await itx.original_response()

    # ---- lệnh nhiệm vụ ----------------------------------------------------------------
    @nhiem_vu.command(name="danh_sach", description="Bảng nhiệm vụ và tiến độ của bạn")
    @rate_limit(3)
    async def nv_ds(self, itx: discord.Interaction):
        b = await self.call(itx, self.g.quests.board, itx.user.id)
        if b is not FAILED:
            await itx.response.send_message(embed=self.ui.quests(b), ephemeral=True)

    @nhiem_vu.command(name="nhan", description="Nhận một nhiệm vụ (tiến độ tự cập nhật khi chơi, hoàn thành tự trả thưởng)")
    @app_commands.choices(nhiem_vu=[app_commands.Choice(name=q["name"], value=k) for k, q in QUESTS.items()])
    @rate_limit(3)
    async def nv_nhan(self, itx: discord.Interaction, nhiem_vu: app_commands.Choice[str]):
        if await self.call(itx, self.g.quests.accept, itx.user.id, nhiem_vu.value) is not FAILED:
            await itx.response.send_message(embed=self.ui.success("Đã nhận nhiệm vụ", f"**{nhiem_vu.name}**"), ephemeral=True)


async def setup(bot):
    await bot.add_cog(EventCog(bot))

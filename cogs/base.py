"""Nền tảng chung cho mọi Cog: gọi engine an toàn, xử lý lỗi nghiệp vụ, view chỉ chủ nhân được bấm."""
from __future__ import annotations

import discord
from discord.ext import commands

from core.errors import GameError


class _Failed:
    def __repr__(self):
        return "FAILED"


FAILED = _Failed()


class OwnedView(discord.ui.View):
    def __init__(self, owner_id: int, timeout: float = 600):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.message: discord.Message | None = None

    async def interaction_check(self, itx: discord.Interaction) -> bool:
        if itx.user.id != self.owner_id:
            await itx.response.send_message("Đây không phải bảng điều khiển của bạn.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class GameCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def g(self):
        return self.bot.game

    @property
    def ui(self):
        return self.bot.ui

    async def call(self, itx: discord.Interaction, fn, *args, **kwargs):
        """Chạy hàm engine trong thread. Lỗi nghiệp vụ -> báo riêng cho người dùng, trả FAILED."""
        try:
            return await self.bot.db.call(fn, *args, **kwargs)
        except GameError as e:
            await self.reply(itx, embed=self.ui.error(str(e)), ephemeral=True)
            return FAILED

    async def reply(self, itx: discord.Interaction, **kw):
        if itx.response.is_done():
            return await itx.followup.send(**kw)
        return await itx.response.send_message(**kw)

    async def flush(self, itx: discord.Interaction):
        """Gửi các thông báo phát sinh từ hệ thống khác (nhiệm vụ, thành tựu, phục tô...)."""
        notes = self.g.drain_notices(itx.user.id)
        if notes:
            await itx.followup.send(embed=self.ui.notices(notes), ephemeral=True)

    async def edit(self, itx: discord.Interaction, view=None, **kw):
        await itx.response.edit_message(view=view, **kw)
        if view is not None:
            view.message = itx.message

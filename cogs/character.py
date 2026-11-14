"""Nhân vật: tạo, hồ sơ, nghỉ ngơi, lịch sử, thành tựu, bảng xếp hạng, trợ giúp."""
from __future__ import annotations

import discord
from discord import app_commands

from cogs.base import FAILED, GameCog, OwnedView
from core.guards import rate_limit
from data.basics import ORIGINS


class OriginView(OwnedView):
    def __init__(self, cog, owner_id, name):
        super().__init__(owner_id, 300)
        self.cog, self.name = cog, name
        sel = discord.ui.Select(placeholder="Chọn xuất thân...", options=[
            discord.SelectOption(label=o["name"], value=k, description=o["desc"][:100]) for k, o in ORIGINS.items()])
        sel.callback = self.chosen
        self.add_item(sel)

    async def chosen(self, itx: discord.Interaction):
        cog = self.cog
        p = await cog.call(itx, cog.g.players.create, itx.user.id, self.name, itx.data["values"][0])
        if p is FAILED:
            return
        self.stop()
        await itx.response.edit_message(embed=cog.ui.success(
            "Hành trình bắt đầu", f"**{p['name']}** bước vào Hắc Thủy Thành. Thế giới đang phục tô.\n"
                                  "Hãy dùng `/ho_so`, `/ban_do`, `/di_chuyen` và `/kham_pha`. "
                                  "Gia nhập Tổng Bộ bằng `/to_chuc gia_nhap` để nhận nhiệm vụ."), view=None)


class ProfileView(OwnedView):
    def __init__(self, cog, owner_id, target_id):
        super().__init__(owner_id, 300)
        self.cog, self.target = cog, target_id

    @discord.ui.button(label="Lịch sử", style=discord.ButtonStyle.secondary)
    async def hist(self, itx: discord.Interaction, _):
        rows = await self.cog.call(itx, self.cog.g.players.history, self.target, 10)
        if rows is not FAILED:
            await itx.response.send_message(embed=self.cog.ui.history(rows), ephemeral=True)

    @discord.ui.button(label="Thành tựu", style=discord.ButtonStyle.secondary)
    async def ach(self, itx: discord.Interaction, _):
        rows = await self.cog.call(itx, self.cog.g.progress.achievements, self.target)
        if rows is not FAILED:
            await itx.response.send_message(embed=self.cog.ui.achievements(rows), ephemeral=True)


class DeleteView(OwnedView):
    def __init__(self, cog, owner_id):
        super().__init__(owner_id, 120)
        self.cog = cog

    @discord.ui.button(label="Xóa vĩnh viễn", style=discord.ButtonStyle.danger)
    async def confirm(self, itx: discord.Interaction, _):
        r = await self.cog.call(itx, self.cog.g.players.delete, itx.user.id)
        if r is FAILED:
            return
        self.stop()
        await itx.response.edit_message(embed=self.cog.ui.success(
            "Đã xóa nhân vật", f"**{r['name']}** đã biến mất. {r['ghosts_released']} lệ quỷ tuột khỏi tay, "
                               f"{r['sealed_lost']} Vật Chứa Vàng mất theo. Bạn có thể `/tao_nhan_vat` lại."), view=None)

    @discord.ui.button(label="Hủy", style=discord.ButtonStyle.secondary)
    async def cancel(self, itx: discord.Interaction, _):
        self.stop()
        await itx.response.edit_message(embed=self.cog.ui.embed("Đã hủy", "Nhân vật của bạn vẫn còn nguyên.", "info", "ui_thanh_cong"),
                                        view=None)


class CharacterCog(GameCog):
    @app_commands.command(name="tao_nhan_vat", description="Tạo nhân vật và bắt đầu hành trình Ngự Quỷ Giả")
    @app_commands.describe(ten="Tên nhân vật (2-24 ký tự)")
    @rate_limit(5)
    async def tao(self, itx: discord.Interaction, ten: str):
        if await self.bot.db.call(self.g.players.exists, itx.user.id):
            return await itx.response.send_message(embed=self.ui.error("Bạn đã có nhân vật rồi."), ephemeral=True)
        lines = "\n".join(f"**{o['name']}** — {o['desc']}" for o in ORIGINS.values())
        view = OriginView(self, itx.user.id, ten)
        await itx.response.send_message(embed=self.ui.embed(f"Tạo nhân vật: {ten}", lines, "main", "char_nguoi_thuong"),
                                        view=view, ephemeral=True)
        view.message = await itx.original_response()

    @app_commands.command(name="ho_so", description="Xem hồ sơ nhân vật")
    @app_commands.describe(nguoi="Người chơi muốn xem (mặc định là bạn)")
    @rate_limit(3)
    async def ho_so(self, itx: discord.Interaction, nguoi: discord.User | None = None):
        target = nguoi or itx.user
        d = await self.call(itx, self.g.players.profile, target.id)
        if d is FAILED:
            return
        view = ProfileView(self, itx.user.id, target.id)
        await itx.response.send_message(embed=self.ui.profile(d, target.mention), view=view)
        view.message = await itx.original_response()
        await self.flush(itx)

    @app_commands.command(name="nghi_ngoi", description="Nghỉ trong nhà an toàn (15 tiền cổ): hồi sức và giảm phục tô")
    @rate_limit(3)
    async def nghi(self, itx: discord.Interaction):
        p = await self.call(itx, self.g.econ.rest, itx.user.id)
        if p is FAILED:
            return
        await itx.response.send_message(embed=self.ui.success(
            "Đã nghỉ ngơi", f"Thể chất {p['hp']}/{p['max_hp']}, tinh thần {p['sanity']}/{p['max_sanity']}, "
                            f"nhiễm linh dị {p['corruption']}%. Lệ quỷ trong người bạn dịu đi."))
        await self.flush(itx)

    @app_commands.command(name="lich_su", description="Lịch sử sự kiện của bạn")
    @rate_limit(3)
    async def lich_su(self, itx: discord.Interaction):
        rows = await self.call(itx, self.g.players.history, itx.user.id, 12)
        if rows is not FAILED:
            await itx.response.send_message(embed=self.ui.history(rows), ephemeral=True)

    @app_commands.command(name="thanh_tuu", description="Danh sách thành tựu")
    @rate_limit(3)
    async def thanh_tuu(self, itx: discord.Interaction):
        rows = await self.call(itx, self.g.progress.achievements, itx.user.id)
        if rows is not FAILED:
            await itx.response.send_message(embed=self.ui.achievements(rows), ephemeral=True)

    @app_commands.command(name="bxh", description="Bảng xếp hạng")
    @app_commands.choices(loai=[app_commands.Choice(name=n, value=v) for n, v in (
        ("Cấp độ", "level"), ("Danh tiếng", "reputation"), ("Phong ấn", "seals"), ("Manh mối", "clues"),
        ("Cống hiến Tổng Bộ", "contribution"))])
    @rate_limit(3)
    async def bxh(self, itx: discord.Interaction, loai: app_commands.Choice[str]):
        rows = await self.call(itx, self.g.progress.board, loai.value)
        if rows is not FAILED:
            await itx.response.send_message(embed=self.ui.board(loai.value, rows))

    @app_commands.command(name="xoa_nhan_vat", description="Xóa vĩnh viễn nhân vật và toàn bộ dữ liệu của bạn")
    @app_commands.describe(xac_nhan="Gõ đúng tên nhân vật để xác nhận")
    @rate_limit(10)
    async def xoa_nhan_vat(self, itx: discord.Interaction, xac_nhan: str):
        p = await self.call(itx, self.g.players.require_free, itx.user.id)
        if p is FAILED:
            return
        if xac_nhan.strip() != p["name"]:
            return await itx.response.send_message(embed=self.ui.error(f"Tên xác nhận không khớp. Hãy gõ đúng: {p['name']}"), ephemeral=True)
        view = DeleteView(self, itx.user.id)
        await itx.response.send_message(embed=self.ui.embed(
            "Xóa nhân vật?", f"**{p['name']}** (cấp {p['level']}) sẽ bị xóa vĩnh viễn cùng túi đồ, lịch sử, thành tựu, "
                             "Vật Chứa Vàng. Lệ quỷ bạn đang giữ sẽ tuột khỏi tay. Không thể hoàn tác.", "bad", "ui_nguy_hiem"),
            view=view, ephemeral=True)
        view.message = await itx.original_response()

    @app_commands.command(name="tro_giup", description="Danh sách lệnh và cách chơi")
    @rate_limit(3)
    async def tro_giup(self, itx: discord.Interaction):
        await itx.response.send_message(embed=self.ui.help(), ephemeral=True)


async def setup(bot):
    await bot.add_cog(CharacterCog(bot))

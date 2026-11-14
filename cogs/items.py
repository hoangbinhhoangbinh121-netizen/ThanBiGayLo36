"""Vật phẩm, cửa hàng và giao dịch giữa người chơi."""
from __future__ import annotations

import discord
from discord import app_commands

from cogs.base import FAILED, GameCog, OwnedView
from core.guards import rate_limit
from data.basics import ITEMS

ITEM_CHOICES = [app_commands.Choice(name=v["name"], value=k) for k, v in ITEMS.items()]
BUY_CHOICES = [app_commands.Choice(name=f"{v['name']} ({v['buy']})", value=k) for k, v in ITEMS.items() if v.get("buy")]


class UseItemView(OwnedView):
    def __init__(self, cog, owner_id, rows):
        super().__init__(owner_id, 300)
        self.cog = cog
        usable = [r for r in rows if "use" in ITEMS[r["item_id"]] or r["item_id"] in ("bua_ap_che", "thu_linh_di")]
        if usable:
            sel = discord.ui.Select(placeholder="Dùng vật phẩm...", options=[
                discord.SelectOption(label=f"{ITEMS[r['item_id']]['name']} ×{r['qty']}", value=r["item_id"],
                                     description=ITEMS[r["item_id"]]["desc"][:100],
                                     emoji=cog.ui.emoji.partial(ITEMS[r["item_id"]]["emoji"])) for r in usable][:25])
            sel.callback = self.chosen
            self.add_item(sel)

    async def chosen(self, itx: discord.Interaction):
        item = itx.data["values"][0]
        if item == "bua_ap_che":
            return await itx.response.send_message(embed=self.cog.ui.embed(
                "Bùa Áp Chế", "Dùng `/quy ap_che` để chọn lệ quỷ cần dán bùa.", "info", "ui_phong_an"), ephemeral=True)
        lines = await self.cog.call(itx, self.cog.g.inv.use, itx.user.id, item)
        if lines is FAILED:
            return
        await itx.response.send_message(embed=self.cog.ui.success("Đã dùng vật phẩm", "\n".join(lines)))
        await self.cog.flush(itx)


class TradeView(discord.ui.View):
    def __init__(self, cog, trade_id, target_id, from_id):
        super().__init__(timeout=600)
        self.cog, self.tid, self.target, self.sender = cog, trade_id, target_id, from_id

    async def interaction_check(self, itx):
        if itx.user.id not in (self.target, self.sender):
            await itx.response.send_message("Giao dịch này không dành cho bạn.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Chấp nhận", style=discord.ButtonStyle.success)
    async def accept(self, itx: discord.Interaction, _):
        if itx.user.id != self.target:
            return await itx.response.send_message("Chỉ người nhận mới chấp nhận được.", ephemeral=True)
        r = await self.cog.call(itx, self.cog.g.econ.accept, itx.user.id, self.tid)
        if r is FAILED:
            return
        self.stop()
        await itx.response.edit_message(embed=self.cog.ui.success("Giao dịch hoàn tất", f"Giao dịch #{self.tid} đã thực hiện."), view=None)
        await self.cog.flush(itx)

    @discord.ui.button(label="Từ chối / Hủy", style=discord.ButtonStyle.danger)
    async def decline(self, itx: discord.Interaction, _):
        r = await self.cog.call(itx, self.cog.g.econ.decline, itx.user.id, self.tid)
        if r is FAILED:
            return
        self.stop()
        await itx.response.edit_message(embed=self.cog.ui.embed("Giao dịch đã đóng", f"Giao dịch #{self.tid} bị hủy.", "info", "ui_that_bai"), view=None)


class ItemCog(GameCog):
    @app_commands.command(name="kho_do", description="Xem túi đồ")
    @rate_limit(3)
    async def kho_do(self, itx: discord.Interaction):
        def work():
            p = self.g.players.refresh(itx.user.id)
            return p["coins"], self.g.inv.list(itx.user.id)
        r = await self.call(itx, work)
        if r is FAILED:
            return
        view = UseItemView(self, itx.user.id, r[1])
        kw = {"view": view} if view.children else {}
        await itx.response.send_message(embed=self.ui.inventory(r[1], r[0]), ephemeral=True, **kw)
        if kw:
            view.message = await itx.original_response()

    @app_commands.command(name="dung_vat_pham", description="Dùng một vật phẩm trong túi")
    @app_commands.choices(vat_pham=ITEM_CHOICES)
    @rate_limit(3)
    async def dung(self, itx: discord.Interaction, vat_pham: app_commands.Choice[str]):
        if vat_pham.value == "bua_ap_che":
            return await itx.response.send_message(embed=self.ui.embed("Bùa Áp Chế", "Dùng `/quy ap_che`.", "info", "ui_phong_an"),
                                                   ephemeral=True)
        lines = await self.call(itx, self.g.inv.use, itx.user.id, vat_pham.value)
        if lines is not FAILED:
            await itx.response.send_message(embed=self.ui.success("Đã dùng vật phẩm", "\n".join(lines)))
            await self.flush(itx)

    @app_commands.command(name="cua_hang", description="Xem cửa hàng Tổng Bộ (chỉ ở Khu Trung Tâm)")
    @rate_limit(3)
    async def cua_hang(self, itx: discord.Interaction):
        coins = await self.call(itx, lambda: self.g.players.refresh(itx.user.id)["coins"])
        if coins is not FAILED:
            await itx.response.send_message(embed=self.ui.shop(self.g.econ.stock(), coins), ephemeral=True)

    @app_commands.command(name="mua", description="Mua vật phẩm ở cửa hàng")
    @app_commands.choices(vat_pham=BUY_CHOICES)
    @app_commands.describe(so_luong="1-20")
    @rate_limit(2)
    async def mua(self, itx: discord.Interaction, vat_pham: app_commands.Choice[str], so_luong: app_commands.Range[int, 1, 20] = 1):
        cost = await self.call(itx, self.g.econ.buy, itx.user.id, vat_pham.value, so_luong)
        if cost is not FAILED:
            await itx.response.send_message(embed=self.ui.success("Đã mua", f"{self.ui.item(vat_pham.value, so_luong)} — {cost} tiền cổ."),
                                            ephemeral=True)
            await self.flush(itx)

    @app_commands.command(name="ban", description="Bán vật phẩm cho cửa hàng")
    @app_commands.choices(vat_pham=ITEM_CHOICES)
    @rate_limit(2)
    async def ban(self, itx: discord.Interaction, vat_pham: app_commands.Choice[str], so_luong: app_commands.Range[int, 1, 99] = 1):
        gain = await self.call(itx, self.g.econ.sell, itx.user.id, vat_pham.value, so_luong)
        if gain is not FAILED:
            await itx.response.send_message(embed=self.ui.success("Đã bán", f"{self.ui.item(vat_pham.value, so_luong)} — nhận {gain} tiền cổ."),
                                            ephemeral=True)

    giao_dich = app_commands.Group(name="giao_dich", description="Trao đổi vật phẩm và tiền cổ với người chơi khác")

    @giao_dich.command(name="moi", description="Gửi lời mời giao dịch (người nhận phải chấp nhận)")
    @app_commands.choices(cho_vat_pham=ITEM_CHOICES, doi_vat_pham=ITEM_CHOICES)
    @app_commands.describe(nguoi="Người nhận", cho_vat_pham="Bạn đưa vật phẩm", cho_so_luong="Số lượng bạn đưa",
                           cho_xu="Tiền cổ bạn đưa", doi_vat_pham="Bạn muốn nhận vật phẩm", doi_so_luong="Số lượng muốn nhận",
                           doi_xu="Tiền cổ muốn nhận")
    @rate_limit(5)
    async def moi(self, itx: discord.Interaction, nguoi: discord.User,
                  cho_vat_pham: app_commands.Choice[str] | None = None, cho_so_luong: app_commands.Range[int, 1, 99] = 1,
                  cho_xu: app_commands.Range[int, 0, 100000] = 0, doi_vat_pham: app_commands.Choice[str] | None = None,
                  doi_so_luong: app_commands.Range[int, 1, 99] = 1, doi_xu: app_commands.Range[int, 0, 100000] = 0):
        give = {"item": cho_vat_pham.value if cho_vat_pham else None, "qty": cho_so_luong if cho_vat_pham else 0, "coins": cho_xu}
        want = {"item": doi_vat_pham.value if doi_vat_pham else None, "qty": doi_so_luong if doi_vat_pham else 0, "coins": doi_xu}
        tid = await self.call(itx, self.g.econ.offer, itx.user.id, nguoi.id, give, want)
        if tid is FAILED:
            return
        t = await self.bot.db.call(self.g.db.one, "SELECT * FROM trades WHERE id=?", (tid,))
        view = TradeView(self, tid, nguoi.id, itx.user.id)
        await itx.response.send_message(content=f"{nguoi.mention}, bạn có một lời mời giao dịch.",
                                        embed=self.ui.trade(t, (itx.user.display_name, nguoi.display_name)), view=view)

    @giao_dich.command(name="danh_sach", description="Lời mời giao dịch đang chờ bạn")
    @rate_limit(3)
    async def ds(self, itx: discord.Interaction):
        rows = await self.call(itx, self.g.econ.pending_for, itx.user.id)
        if rows is FAILED:
            return
        if not rows:
            return await itx.response.send_message(embed=self.ui.embed("Giao dịch", "Không có lời mời nào.", "info", "item_tien_co"), ephemeral=True)
        await itx.response.send_message(embeds=[self.ui.trade(t, (f"<@{t['from_user']}>", "Bạn")) for t in rows[:5]], ephemeral=True)

    @giao_dich.command(name="chap_nhan", description="Chấp nhận giao dịch theo mã")
    @rate_limit(3)
    async def chap_nhan(self, itx: discord.Interaction, ma: int):
        r = await self.call(itx, self.g.econ.accept, itx.user.id, ma)
        if r is not FAILED:
            await itx.response.send_message(embed=self.ui.success("Giao dịch hoàn tất", f"Đã thực hiện giao dịch #{ma}."))
            await self.flush(itx)

    @giao_dich.command(name="tu_choi", description="Từ chối hoặc hủy giao dịch theo mã")
    @rate_limit(3)
    async def tu_choi(self, itx: discord.Interaction, ma: int):
        r = await self.call(itx, self.g.econ.decline, itx.user.id, ma)
        if r is not FAILED:
            await itx.response.send_message(embed=self.ui.embed("Đã đóng", f"Giao dịch #{ma} bị hủy.", "info", "ui_that_bai"), ephemeral=True)


async def setup(bot):
    await bot.add_cog(ItemCog(bot))

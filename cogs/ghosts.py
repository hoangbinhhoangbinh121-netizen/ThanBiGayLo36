"""Ngự Quỷ Giả: danh sách lệ quỷ, bách khoa, năng lực, áp chế, bàn giao, cứu đồng đội."""
from __future__ import annotations

import discord
from discord import app_commands

from cogs.base import FAILED, GameCog, OwnedView
from core.guards import rate_limit
from data.ghosts import GHOSTS


def ghost_options(ui, rows, with_res=True):
    out = []
    for g in rows:
        gd = GHOSTS[g["ghost_id"]]
        out.append(discord.SelectOption(label=f"{gd['name']} (mã {g['id']})", value=str(g["id"]),
                                        description=f"Phục tô {g['resurrection']:.0f}%" if with_res else gd["rank"],
                                        emoji=ui.emoji.partial(gd["emoji"])))
    return out[:25]


class PickGhostView(OwnedView):
    """Chọn một lệ quỷ rồi chạy hành động `action(uid, inst_id)`."""
    def __init__(self, cog, owner_id, rows, placeholder, action, title, with_res=True):
        super().__init__(owner_id, 300)
        self.cog, self.action, self.title = cog, action, title
        sel = discord.ui.Select(placeholder=placeholder, options=ghost_options(cog.ui, rows, with_res))
        sel.callback = self.chosen
        self.add_item(sel)

    async def chosen(self, itx: discord.Interaction):
        r = await self.cog.call(itx, self.action, itx.user.id, int(itx.data["values"][0]))
        if r is FAILED:
            return
        self.stop()
        lines = r if isinstance(r, list) else [f"+{r['coins']} tiền cổ, +{r['rep']} danh tiếng. Kho Tổng Bộ nhận thêm một oan hồn."]
        await itx.response.edit_message(embed=self.cog.ui.success(self.title, "\n".join(lines)), view=None)
        await self.cog.flush(itx)


class PowerView(OwnedView):
    def __init__(self, cog, owner_id, owned):
        super().__init__(owner_id, 300)
        self.cog, self.power, self.target = cog, None, None
        popts = [discord.SelectOption(label=f"{pw['name']} ({GHOSTS[g['ghost_id']]['name']})"[:100], value=f"{g['id']}:{pw['id']}",
                                      description=pw["desc"][:100], emoji=cog.ui.emoji.partial(GHOSTS[g["ghost_id"]]["emoji"]))
                 for g in owned for pw in GHOSTS[g["ghost_id"]]["powers"]][:25]
        s1 = discord.ui.Select(placeholder="1. Chọn năng lực", options=popts, row=0)
        s1.callback = self.pick_power
        self.add_item(s1)
        if len(owned) > 1:
            s2 = discord.ui.Select(placeholder="2. (Tùy chọn) Lệ quỷ mục tiêu để áp chế", options=ghost_options(cog.ui, owned), row=1)
            s2.callback = self.pick_target
            self.add_item(s2)
        go = discord.ui.Button(label="Kích hoạt", style=discord.ButtonStyle.danger, row=2)
        go.callback = self.go
        self.add_item(go)

    async def pick_power(self, itx):
        self.power = itx.data["values"][0]
        await itx.response.defer()

    async def pick_target(self, itx):
        self.target = int(itx.data["values"][0])
        await itx.response.defer()

    async def go(self, itx):
        if not self.power:
            return await itx.response.send_message("Hãy chọn một năng lực trước.", ephemeral=True)
        inst, power = self.power.split(":")
        lines = await self.cog.call(itx, self.cog.g.ghosts.use_power, itx.user.id, int(inst), power, self.target)
        if lines is FAILED:
            return
        self.stop()
        await itx.response.edit_message(embed=self.cog.ui.embed("Năng lực linh dị", "\n".join(lines), "mystic", "ghost_quy_vuc"), view=None)
        await self.cog.flush(itx)


class GhostCog(GameCog):
    quy = app_commands.Group(name="quy", description="Lệ quỷ và năng lực Ngự Quỷ Giả")

    @quy.command(name="danh_sach", description="Lệ quỷ bạn đang giữ, phục tô và cân bằng linh dị")
    @rate_limit(3)
    async def danh_sach(self, itx: discord.Interaction):
        d = await self.call(itx, self.g.players.profile, itx.user.id)
        if d is not FAILED:
            await itx.response.send_message(embed=self.ui.ghost_list(d["ghosts"], d["sealed"], d["slots"], d["balance"]))
            await self.flush(itx)

    @quy.command(name="thong_tin", description="Bách khoa lệ quỷ (mở dần theo manh mối bạn tìm được)")
    @app_commands.choices(quy=[app_commands.Choice(name=g["name"], value=k) for k, g in GHOSTS.items()])
    @rate_limit(3)
    async def thong_tin(self, itx: discord.Interaction, quy: app_commands.Choice[str]):
        data = await self.call(itx, self.g.ghosts.codex, itx.user.id, quy.value)
        if data is not FAILED:
            await itx.response.send_message(embed=self.ui.codex(data), ephemeral=True)

    @quy.command(name="nang_luc", description="Dùng năng lực của lệ quỷ (làm phục tô tăng nhanh)")
    @rate_limit(3)
    async def nang_luc(self, itx: discord.Interaction):
        owned = await self.call(itx, lambda: (self.g.players.require_free(itx.user.id), self.g.ghosts.owned(itx.user.id))[1])
        if owned is FAILED:
            return
        if not owned:
            return await itx.response.send_message(embed=self.ui.error("Bạn chưa khống chế lệ quỷ nào."), ephemeral=True)
        view = PowerView(self, itx.user.id, owned)
        await itx.response.send_message(embed=self.ui.embed(
            "Năng lực linh dị", "Mỗi lần dùng, lệ quỷ phục tô thêm. Đến 100% nó thoát ra và bạn mất kiểm soát. "
                                "Dùng khi còn ổn định (dưới 60%) sẽ tích lũy thức tỉnh.", "mystic", "ghost_quy_vuc"),
            view=view, ephemeral=True)
        view.message = await itx.original_response()

    @quy.command(name="ap_che", description="Dán Bùa Áp Chế lên lệ quỷ của bạn (giảm 30 phục tô)")
    @rate_limit(3)
    async def ap_che(self, itx: discord.Interaction):
        owned = await self.call(itx, self.g.ghosts.owned, itx.user.id)
        if owned is FAILED:
            return
        if not owned:
            return await itx.response.send_message(embed=self.ui.error("Bạn chưa khống chế lệ quỷ nào."), ephemeral=True)
        view = PickGhostView(self, itx.user.id, owned, "Chọn lệ quỷ cần áp chế",
                             lambda uid, inst: self.g.inv.use(uid, "bua_ap_che", inst), "Áp chế")
        await itx.response.send_message(embed=self.ui.embed("Áp chế", "Chọn lệ quỷ để dán bùa.", "mystic", "ui_phong_an"),
                                        view=view, ephemeral=True)
        view.message = await itx.original_response()

    @quy.command(name="ban_giao", description="Bàn giao Vật Chứa Vàng đã niêm phong cho kho Tổng Bộ để nhận thưởng")
    @rate_limit(3)
    async def ban_giao(self, itx: discord.Interaction):
        sealed = await self.call(itx, self.g.ghosts.sealed_by, itx.user.id)
        if sealed is FAILED:
            return
        if not sealed:
            return await itx.response.send_message(embed=self.ui.error("Bạn không giữ Vật Chứa Vàng nào có lệ quỷ."), ephemeral=True)
        view = PickGhostView(self, itx.user.id, sealed, "Chọn Vật Chứa Vàng để bàn giao", self.g.ghosts.hand_over,
                             "Đã bàn giao", with_res=False)
        await itx.response.send_message(embed=self.ui.embed("Bàn giao Tổng Bộ", "Chỉ thành viên Tổng Bộ mới bàn giao được.",
                                                            "info", "item_vat_phong_an"), view=view, ephemeral=True)
        view.message = await itx.original_response()

    @app_commands.command(name="ap_che_dong_doi", description="Dùng Bùa Áp Chế kéo đồng đội đang mất kiểm soát (cùng địa điểm)")
    @app_commands.describe(nguoi="Đồng đội đang mất kiểm soát")
    @rate_limit(5)
    async def ap_che_dong_doi(self, itx: discord.Interaction, nguoi: discord.User):
        r = await self.call(itx, self.g.ghosts.rescue, itx.user.id, nguoi.id)
        if r is not FAILED:
            await itx.response.send_message(embed=self.ui.success("Cứu được đồng đội", f"{nguoi.mention} đã thoát khỏi mất kiểm soát."))
            await self.flush(itx)


async def setup(bot):
    await bot.add_cog(GhostCog(bot))

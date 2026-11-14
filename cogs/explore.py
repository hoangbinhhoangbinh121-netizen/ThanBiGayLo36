"""Khám phá và đối mặt lệ quỷ. Trạng thái đối mặt nằm trong DB nên /doi_mat luôn khôi phục được."""
from __future__ import annotations

import discord
from discord import app_commands

from cogs.base import FAILED, GameCog, OwnedView
from core.guards import rate_limit
from data.ghosts import GHOSTS
from data.locations import LOCATIONS

END_TEXT = {
    "death": ("Bạn đã chết", "bad", "ui_that_bai"),
    "died": ("Bạn đã chết", "bad", "ui_that_bai"),
    "saved": ("Hình Nhân vỡ vụn", "warn", "item_hinh_nhan"),
    "breakdown": ("Mất kiểm soát", "bad", "char_mat_kiem_soat"),
    "resurrected": ("Lệ quỷ phục tô", "bad", "char_mat_kiem_soat"),
    "escaped": ("Thoát được", "info", "ui_thanh_cong"),
}


class ExploreView(OwnedView):
    def __init__(self, cog, owner_id):
        super().__init__(owner_id, 600)
        self.cog = cog
        for mode, label, icon in (("tham_do", "Thăm dò", "ui_kham_pha"), ("dieu_tra", "Điều tra manh mối", "ui_nhiem_vu"),
                                  ("tim_do", "Tìm vật phẩm", "item_linh_di_vat")):
            b = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary, emoji=cog.ui.emoji.partial(icon))
            b.callback = self._make(mode)
            self.add_item(b)

    def _make(self, mode):
        async def cb(itx: discord.Interaction):
            await self.cog.do_explore(itx, mode, self)
        return cb


class EncounterView(OwnedView):
    def __init__(self, cog, uid, v):
        super().__init__(uid, 900)
        self.cog, self.uid, self.v = cog, uid, v
        ui = cog.ui
        if v["phase"] == "fight":
            opts = [discord.SelectOption(label=o.label[:100], value=o.id, description=(o.desc[:100] or None))
                    for o in v["scene"].options][:25]
            sel = discord.ui.Select(placeholder="Chọn hành động...", options=opts, row=0)
            sel.callback = self.on_action
            self.add_item(sel)
            if v["powers"]:
                popts = [discord.SelectOption(
                    label=f"{pw['name']} ({GHOSTS[g['ghost_id']]['name']})"[:100], value=f"{g['id']}:{pw['id']}",
                    description=f"Phục tô hiện {g['resurrection']:.0f}%, tốn ~{pw['cost']}%",
                    emoji=ui.emoji.partial(GHOSTS[g["ghost_id"]]["emoji"])) for g, pw in v["powers"]][:25]
                ps = discord.ui.Select(placeholder="Dùng năng lực Ngự Quỷ...", options=popts, row=1)
                ps.callback = self.on_power
                self.add_item(ps)
            flee = discord.ui.Button(label="Bỏ chạy", style=discord.ButtonStyle.danger, row=2)
            flee.callback = self.on_flee
            self.add_item(flee)
        else:
            held = v["already_held"]
            bind = discord.ui.Button(label="Khống chế", style=discord.ButtonStyle.success, disabled=held,
                                     emoji=ui.emoji.partial("char_ngu_quy_gia"), row=0)
            bind.callback = self.on_bind
            seal = discord.ui.Button(label="Phong ấn", style=discord.ButtonStyle.primary, disabled=not v["has_container"],
                                     emoji=ui.emoji.partial("ui_phong_an"), row=0)
            seal.callback = self.on_seal
            leave = discord.ui.Button(label="Rời đi", style=discord.ButtonStyle.secondary, row=0)
            leave.callback = self.on_leave
            for b in (bind, seal, leave):
                self.add_item(b)

    async def on_action(self, itx):
        res = await self.cog.call(itx, self.cog.g.enc.act, self.uid, itx.data["values"][0])
        await self.cog.after(itx, self, res)

    async def on_power(self, itx):
        inst, power = itx.data["values"][0].split(":")
        res = await self.cog.call(itx, self.cog.g.enc.use_power, self.uid, int(inst), power)
        await self.cog.after(itx, self, res)

    async def on_flee(self, itx):
        res = await self.cog.call(itx, self.cog.g.enc.flee, self.uid)
        await self.cog.after(itx, self, res)

    async def on_bind(self, itx):
        r = await self.cog.call(itx, self.cog.g.enc.bind, self.uid)
        if r is FAILED:
            return
        gd = GHOSTS[r["ghost"]]
        if r["success"]:
            extra = []
            if r["first"]:
                extra.append("Bạn đã trở thành **Ngự Quỷ Giả**.")
            if r["over"]:
                extra.append("Bạn giữ quá nhiều lệ quỷ so với giới hạn: nhiễm linh dị tăng và phục tô nhanh hơn.")
            emb = self.cog.ui.encounter_end(f"Đã khống chế {gd['name']}",
                                            [f"Tỷ lệ thành công: {r['chance'] * 100:.0f}%.", *extra], "good", gd["emoji"])
        else:
            emb = self.cog.ui.encounter_end("Khống chế thất bại", [f"{gd['name']} vùng khỏi tay bạn (tỷ lệ {r['chance'] * 100:.0f}%).",
                                                                  "-20 tinh thần, -10 thể chất, +8 nhiễm linh dị."], "bad", "ui_that_bai")
        self.stop()
        await itx.response.edit_message(embed=emb, view=None)
        await self.cog.flush(itx)

    async def on_seal(self, itx):
        r = await self.cog.call(itx, self.cog.g.enc.seal, self.uid)
        if r is FAILED:
            return
        gd = GHOSTS[r["ghost"]]
        self.stop()
        await itx.response.edit_message(embed=self.cog.ui.encounter_end(
            f"Đã phong ấn {gd['name']}", [f"+{r['exp']} EXP, +{r['rep']} danh tiếng, +{r['coins']} tiền cổ.",
                                         "Mang Vật Chứa Vàng về Tổng Bộ bằng `/quy ban_giao` để nhận thêm thưởng."],
            "good", "item_vat_phong_an"), view=None)
        await self.cog.flush(itx)

    async def on_leave(self, itx):
        r = await self.cog.call(itx, self.cog.g.enc.leave, self.uid)
        if r is FAILED:
            return
        self.stop()
        await itx.response.edit_message(embed=self.cog.ui.encounter_end(
            "Rời đi", ["Bạn lặng lẽ rời đi. Lệ quỷ vẫn ở lại nơi này, chờ người kế tiếp."], "info", "ui_kham_pha"), view=None)
        await self.cog.flush(itx)


class ExploreCog(GameCog):
    async def after(self, itx, old_view, res):
        if res is FAILED:
            return
        st = res["status"]
        if st in END_TEXT:
            title, color, icon = END_TEXT[st]
            old_view.stop()
            await itx.response.edit_message(embed=self.ui.encounter_end(title, res["lines"], color, icon), view=None)
            return await self.flush(itx)
        v = await self.call(itx, self.g.enc.view, itx.user.id)
        if v is FAILED:
            return
        old_view.stop()
        await self.edit(itx, EncounterView(self, itx.user.id, v), embed=self.ui.encounter(v, res["lines"]))
        await self.flush(itx)

    async def do_explore(self, itx, mode, old_view):
        res = await self.call(itx, self.g.explore.explore, itx.user.id, mode)
        if res is FAILED:
            return
        old_view.stop()
        if res["encounter"]:
            v = await self.call(itx, self.g.enc.view, itx.user.id)
            if v is not FAILED:
                await self.edit(itx, EncounterView(self, itx.user.id, v), embed=self.ui.encounter(v, res["lines"]))
                return await self.flush(itx)
        await self.edit(itx, ExploreView(self, itx.user.id),
                        embed=self.ui.explore_result(res, LOCATIONS[res["loc"]]["name"]))
        await self.flush(itx)

    @app_commands.command(name="kham_pha", description="Khám phá nơi bạn đang đứng: tìm manh mối, vật phẩm, hoặc đối mặt lệ quỷ")
    @rate_limit(3)
    async def kham_pha(self, itx: discord.Interaction):
        p = await self.call(itx, self.g.players.require_free, itx.user.id)
        if p is FAILED:
            return
        loc = LOCATIONS[p["location_id"]]
        desc = (f"{loc['desc']}\n\nThăm dò: cân bằng. Điều tra manh mối: dễ ra manh mối nhưng tốn tinh thần hơn. "
                f"Tìm vật phẩm: dễ nhặt đồ.\nTinh thần hiện tại: **{p['sanity']}/{p['max_sanity']}**")
        view = ExploreView(self, itx.user.id)
        await itx.response.send_message(embed=self.ui.embed(f"Khám phá — {loc['name']}", desc, "main", loc["emoji"]), view=view)
        view.message = await itx.original_response()

    @app_commands.command(name="doi_mat", description="Quay lại cuộc đối mặt đang dở với lệ quỷ")
    @rate_limit(3)
    async def doi_mat(self, itx: discord.Interaction):
        v = await self.call(itx, self.g.enc.view, itx.user.id)
        if v is FAILED:
            return
        view = EncounterView(self, itx.user.id, v)
        await itx.response.send_message(embed=self.ui.encounter(v), view=view)
        view.message = await itx.original_response()


async def setup(bot):
    await bot.add_cog(ExploreCog(bot))

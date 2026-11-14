"""Thế giới: bản đồ, địa điểm, di chuyển."""
from __future__ import annotations

import discord
from discord import app_commands

from cogs.base import FAILED, GameCog, OwnedView
from core.guards import rate_limit
from data.locations import LOCATIONS


class TravelView(OwnedView):
    def __init__(self, cog, owner_id, options):
        super().__init__(owner_id, 300)
        self.cog = cog
        sel = discord.ui.Select(placeholder="Chọn nơi muốn tới...", options=options)
        sel.callback = self.chosen
        self.add_item(sel)

    async def chosen(self, itx: discord.Interaction):
        cog = self.cog
        dest = itx.data["values"][0]
        cost = await cog.call(itx, cog.g.world.travel, itx.user.id, dest)
        if cost is FAILED:
            return
        self.stop()
        d = await cog.call(itx, cog.g.players.profile, itx.user.id)
        await itx.response.edit_message(embed=await cog.location_embed(d["p"], f"Bạn đã tới nơi (tiêu hao {cost} tinh thần)."),
                                        view=None)
        await cog.flush(itx)


class WorldCog(GameCog):
    async def location_embed(self, p, note=""):
        def work():
            lid = p["location_id"]
            neigh = self.g.world.neighbors(lid)
            names = [f"{self.ui.e(LOCATIONS[n]['emoji'])} {LOCATIONS[n]['name']}" for n in neigh]
            return self.g.world.effective_danger(lid), self.g.world.lock_info(lid), names
        danger, lock, names = await self.bot.db.call(work)
        e = self.ui.location(p, danger, lock, names)
        if note:
            e.description = f"*{note}*\n\n{e.description}"
        return e

    @app_commands.command(name="ban_do", description="Bản đồ thế giới, mức nguy hiểm và các khu phong tỏa")
    @rate_limit(3)
    async def ban_do(self, itx: discord.Interaction):
        def work():
            p = self.g.players.refresh(itx.user.id)
            m = self.g.world.modifiers()
            mods = []
            if m["danger_add"]:
                mods.append(f"Nguy hiểm +{m['danger_add']}")
            if m["clue_bonus"]:
                mods.append(f"Dễ có manh mối +{int(m['clue_bonus'] * 100)}%")
            if m["encounter_add"]:
                mods.append(f"Dễ gặp quỷ +{m['encounter_add']}")
            if m["loot_mult"] > 1:
                mods.append(f"Nhiều đồ rơi x{m['loot_mult']:.1f}")
            return p["location_id"], self.g.world.overview(), self.g.world.unrest(), ", ".join(mods)
        r = await self.call(itx, work)
        if r is not FAILED:
            await itx.response.send_message(embed=self.ui.world_map(r[1], r[0], r[2], r[3]))

    @app_commands.command(name="dia_diem", description="Xem nơi bạn đang đứng")
    @rate_limit(3)
    async def dia_diem(self, itx: discord.Interaction):
        p = await self.call(itx, self.g.players.refresh, itx.user.id)
        if p is not FAILED:
            await itx.response.send_message(embed=await self.location_embed(p))

    @app_commands.command(name="di_chuyen", description="Di chuyển tới địa điểm lân cận (tốn tinh thần)")
    @rate_limit(3)
    async def di_chuyen(self, itx: discord.Interaction):
        def work():
            p = self.g.players.require_free(itx.user.id)
            opts = []
            for n in self.g.world.neighbors(p["location_id"]):
                loc = LOCATIONS[n]
                locked, reason, left = self.g.world.lock_info(n)
                desc = f"Nguy hiểm {self.g.world.effective_danger(n)}" + (f" | PHONG TỎA: {reason}"[:60] if locked else "")
                opts.append((n, loc["name"], desc, loc["emoji"]))
            return opts
        r = await self.call(itx, work)
        if r is FAILED:
            return
        options = [discord.SelectOption(label=name[:100], value=n, description=desc[:100], emoji=self.ui.emoji.partial(emo))
                   for n, name, desc, emo in r]
        view = TravelView(self, itx.user.id, options)
        await itx.response.send_message(embed=self.ui.embed("Di chuyển", "Chọn nơi bạn muốn tới.", "info", "ui_kham_pha"),
                                        view=view, ephemeral=True)
        view.message = await itx.original_response()


async def setup(bot):
    await bot.add_cog(WorldCog(bot))

"""Quản trị: emoji, sao lưu, kênh thông báo, bổ nhiệm, cấp đồ, sự kiện, thống kê. Mọi lệnh kiểm tra quyền admin."""
from __future__ import annotations

import discord
from discord import app_commands

from cogs.base import FAILED, GameCog
from core.guards import admin_only, rate_limit
from data.basics import ITEMS
from data.events import EVENT_DEFS
from data.locations import LOCATIONS


class AdminCog(GameCog):
    admin = app_commands.Group(name="admin", description="Quản trị bot", default_permissions=discord.Permissions(administrator=True),
                               guild_only=True)

    @admin.command(name="emoji", description="Tải/đồng bộ bộ emoji pixel art lên Discord (emoji ứng dụng)")
    @admin_only()
    @rate_limit(10)
    async def emoji(self, itx: discord.Interaction):
        await itx.response.defer(ephemeral=True)
        try:
            created, total = await self.bot.emoji_reg.sync(self.bot)
        except Exception as e:  # noqa: BLE001
            return await itx.followup.send(embed=self.ui.error(f"Không đồng bộ được emoji: {e}\nCần discord.py >= 2.5."),
                                           ephemeral=True)
        await itx.followup.send(embed=self.ui.success("Emoji", f"Đã đồng bộ {total} emoji ({created} mới tải lên). "
                                                              "Giao diện sẽ dùng emoji pixel art từ lệnh kế tiếp."), ephemeral=True)

    @admin.command(name="sao_luu", description="Sao lưu cơ sở dữ liệu ngay")
    @admin_only()
    @rate_limit(10)
    async def sao_luu(self, itx: discord.Interaction):
        await itx.response.defer(ephemeral=True)
        path = await self.bot.db.call(self.bot.db.backup, self.bot.cfg.backup_dir, self.bot.cfg.backup_keep)
        await itx.followup.send(embed=self.ui.success("Sao lưu", f"Đã tạo `{path.name}`."), ephemeral=True)

    @admin.command(name="kenh", description="Đặt kênh nhận thông báo sự kiện thế giới")
    @admin_only()
    async def kenh(self, itx: discord.Interaction, kenh: discord.TextChannel):
        await self.bot.db.call(self.g.db.run, "INSERT INTO world_state(key,value) VALUES('announce_channel',?) "
                                              "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(kenh.id),))
        await itx.response.send_message(embed=self.ui.success("Kênh thông báo", f"Đã đặt {kenh.mention}."), ephemeral=True)

    @admin.command(name="bo_nhiem", description="Bổ nhiệm một người chơi làm Tổng Bộ")
    @admin_only()
    async def bo_nhiem(self, itx: discord.Interaction, nguoi: discord.User):
        if await self.call(itx, self.g.orgs.appoint_head, nguoi.id) is not FAILED:
            await itx.response.send_message(embed=self.ui.success("Bổ nhiệm", f"{nguoi.mention} là Tổng Bộ."), ephemeral=True)

    @admin.command(name="tang", description="Tặng vật phẩm cho người chơi")
    @app_commands.choices(vat_pham=[app_commands.Choice(name=v["name"], value=k) for k, v in ITEMS.items()])
    @admin_only()
    async def tang(self, itx: discord.Interaction, nguoi: discord.User, vat_pham: app_commands.Choice[str],
                   so_luong: app_commands.Range[int, 1, 99] = 1):
        def work():
            self.g.players.get(nguoi.id)
            self.g.inv.add(nguoi.id, vat_pham.value, so_luong)
        if await self.call(itx, work) is not FAILED:
            await itx.response.send_message(embed=self.ui.success("Đã tặng", f"{self.ui.item(vat_pham.value, so_luong)} → {nguoi.mention}"),
                                            ephemeral=True)

    @admin.command(name="mo_khoa", description="Tháo phong tỏa một địa điểm")
    @app_commands.choices(dia_diem=[app_commands.Choice(name=v["name"], value=k) for k, v in LOCATIONS.items() if not v.get("safe")][:25])
    @admin_only()
    async def mo_khoa(self, itx: discord.Interaction, dia_diem: app_commands.Choice[str]):
        await self.bot.db.call(self.g.world.unlock, dia_diem.value)
        await itx.response.send_message(embed=self.ui.success("Đã mở khóa", dia_diem.name), ephemeral=True)

    @admin.command(name="su_kien", description="Kích hoạt một sự kiện thế giới")
    @app_commands.choices(loai=[app_commands.Choice(name=v["title"], value=k) for k, v in EVENT_DEFS.items() if k != "phuc_to"],
                          dia_diem=[app_commands.Choice(name=v["name"], value=k) for k, v in LOCATIONS.items() if not v.get("safe")][:25])
    @admin_only()
    async def su_kien(self, itx: discord.Interaction, loai: app_commands.Choice[str], dia_diem: app_commands.Choice[str] | None = None):
        eid = await self.call(itx, self.g.events.start_event, loai.value, dia_diem.value if dia_diem else None)
        if eid is FAILED:
            return
        await itx.response.send_message(embed=self.ui.success("Đã kích hoạt", f"Sự kiện `#{eid}`: {loai.name}"), ephemeral=True)
        cog = self.bot.get_cog("EventCog")
        if cog:
            await cog.post(await self.bot.db.call(self.g.events.drain_announcements))

    @admin.command(name="xoa_nhan_vat", description="Xóa nhân vật của một người chơi (dọn sạch dữ liệu liên quan)")
    @admin_only()
    async def xoa_nhan_vat(self, itx: discord.Interaction, nguoi: discord.User):
        r = await self.call(itx, self.g.players.delete, nguoi.id)
        if r is not FAILED:
            await itx.response.send_message(embed=self.ui.success("Đã xóa", f"Nhân vật **{r['name']}** của {nguoi.mention}."), ephemeral=True)

    @admin.command(name="thong_ke", description="Thống kê hệ thống")
    @admin_only()
    async def thong_ke(self, itx: discord.Interaction):
        def work():
            d = self.g.db
            return {
                "Người chơi": d.scalar("SELECT COUNT(*) FROM players", default=0),
                "Ngự Quỷ Giả": d.scalar("SELECT COUNT(*) FROM players WHERE is_summoner=1", default=0),
                "Lệ quỷ tự do / bị giữ / niêm phong": "{} / {} / {}".format(*(d.scalar(
                    "SELECT COUNT(*) FROM ghost_instances WHERE state=?", (s,), 0) for s in ("free", "bound", "sealed"))),
                "Sự kiện đang chạy": d.scalar("SELECT COUNT(*) FROM world_events WHERE state='active'", default=0),
                "Bất ổn linh dị": self.g.world.unrest(),
                "Phiên bản schema": d.schema_version(),
                "Emoji đã tải": f"{self.bot.emoji_reg.uploaded()}/{len(self.bot.emoji_reg.map)}",
            }
        r = await self.call(itx, work)
        if r is not FAILED:
            await itx.response.send_message(embed=self.ui.embed("Thống kê", "\n".join(f"**{k}**: {v}" for k, v in r.items()),
                                                                "info", "ui_nhiem_vu"), ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))

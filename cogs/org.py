"""Tổ chức Tổng Bộ: phân cấp quyền hạn, nhiệm vụ tổ chức, báo cáo sự kiện, xếp hạng."""
from __future__ import annotations

import discord
from discord import app_commands

from cogs.base import FAILED, GameCog
from core.guards import rate_limit
from data.basics import MISSION_TYPES, RANKS, REGIONS
from data.ghosts import GHOSTS
from data.locations import LOCATIONS

RANK_CH = [app_commands.Choice(name=v[1], value=k) for k, v in RANKS.items() if k != "tong_bo"]
REGION_CH = [app_commands.Choice(name=n, value=k) for k, n in REGIONS.items()]
TYPE_CH = [app_commands.Choice(name=n, value=k) for k, n in MISSION_TYPES.items()]
LOC_CH = [app_commands.Choice(name=v["name"], value=k) for k, v in LOCATIONS.items() if not v.get("safe")][:25]


class OrgCog(GameCog):
    to_chuc = app_commands.Group(name="to_chuc", description="Tổng Bộ Linh Dị: tổ chức xử lý sự kiện linh dị")

    async def done(self, itx, title, msg, ephemeral=False):
        await itx.response.send_message(embed=self.ui.success(title, msg), ephemeral=ephemeral)
        await self.flush(itx)

    @to_chuc.command(name="gia_nhap", description="Gia nhập Tổng Bộ với cấp Thành Viên")
    @rate_limit(3)
    async def gia_nhap(self, itx: discord.Interaction):
        if await self.call(itx, self.g.orgs.join, itx.user.id) is not FAILED:
            await self.done(itx, "Chào mừng tới Tổng Bộ", "Bạn là Thành Viên. Tích danh tiếng để được thăng cấp. "
                                                         "Xem nhiệm vụ bằng `/to_chuc nhiem_vu`.")

    @to_chuc.command(name="roi", description="Rời Tổng Bộ")
    @rate_limit(3)
    async def roi(self, itx: discord.Interaction):
        if await self.call(itx, self.g.orgs.leave, itx.user.id) is not FAILED:
            await self.done(itx, "Đã rời Tổng Bộ", "Bạn không còn quyền vào các khu phong tỏa.", True)

    @to_chuc.command(name="thong_tin", description="Thông tin tổ chức, ngân quỹ, nhân sự")
    @rate_limit(3)
    async def thong_tin(self, itx: discord.Interaction):
        r = await self.call(itx, lambda: (self.g.orgs.info(), self.g.orgs.member(itx.user.id)))
        if r is not FAILED:
            await itx.response.send_message(embed=self.ui.org(*r))

    @to_chuc.command(name="thanh_vien", description="Danh sách thành viên theo cấp bậc")
    @rate_limit(3)
    async def thanh_vien(self, itx: discord.Interaction):
        rows = await self.call(itx, self.g.orgs.members, 25)
        if rows is not FAILED:
            await itx.response.send_message(embed=self.ui.org_members(rows))

    @to_chuc.command(name="nhiem_vu", description="Nhiệm vụ tổ chức dành cho bạn")
    @rate_limit(3)
    async def nhiem_vu(self, itx: discord.Interaction):
        rows = await self.call(itx, self.g.orgs.missions, itx.user.id)
        if rows is not FAILED:
            await itx.response.send_message(embed=self.ui.missions(rows), ephemeral=True)

    @to_chuc.command(name="nhan_nhiem_vu", description="Nhận một nhiệm vụ tổ chức theo mã")
    @rate_limit(3)
    async def nhan(self, itx: discord.Interaction, ma: int):
        if await self.call(itx, self.g.orgs.take_mission, itx.user.id, ma) is not FAILED:
            await self.done(itx, "Đã nhận nhiệm vụ", f"Nhiệm vụ #{ma} đã giao cho bạn. Tiến độ tự cập nhật khi bạn chơi.", True)

    @to_chuc.command(name="giao_nhiem_vu", description="(Đội Trưởng trở lên) Giao nhiệm vụ, thưởng lấy từ ngân quỹ")
    @app_commands.choices(loai=TYPE_CH, khu_vuc=REGION_CH, dia_diem=LOC_CH,
                          quy=[app_commands.Choice(name=g["name"], value=k) for k, g in GHOSTS.items()])
    @app_commands.describe(so_lan="1-10", thuong="Tiền cổ thưởng (trừ vào ngân quỹ)", giao_cho="Chỉ định một thành viên",
                           gio="Hạn chót (giờ, 1-72)")
    @rate_limit(5)
    async def giao(self, itx: discord.Interaction, loai: app_commands.Choice[str], so_lan: app_commands.Range[int, 1, 10],
                   thuong: app_commands.Range[int, 0, 5000], khu_vuc: app_commands.Choice[str] | None = None,
                   giao_cho: discord.User | None = None, dia_diem: app_commands.Choice[str] | None = None,
                   quy: app_commands.Choice[str] | None = None, gio: app_commands.Range[int, 1, 72] = 24):
        mid = await self.call(itx, self.g.orgs.issue_mission, itx.user.id, loai.value, so_lan, thuong,
                              khu_vuc.value if khu_vuc else None, giao_cho.id if giao_cho else None, gio,
                              dia_diem.value if dia_diem else None, quy.value if quy else None)
        if mid is not FAILED:
            await self.done(itx, "Đã giao nhiệm vụ", f"Nhiệm vụ `#{mid}` đã đăng. Thành viên nhận bằng `/to_chuc nhan_nhiem_vu`.")

    @to_chuc.command(name="bao_cao", description="Nộp báo cáo sự kiện (tối đa 3/ngày); cấp trên duyệt sẽ có thưởng")
    @app_commands.describe(noi_dung="10-500 ký tự")
    @rate_limit(5)
    async def bao_cao(self, itx: discord.Interaction, noi_dung: app_commands.Range[str, 10, 500]):
        rid = await self.call(itx, self.g.orgs.submit_report, itx.user.id, noi_dung)
        if rid is not FAILED:
            await self.done(itx, "Đã nộp báo cáo", f"Báo cáo `#{rid}` đang chờ Người Phụ Trách duyệt.", True)

    @to_chuc.command(name="duyet_bao_cao", description="(Người Phụ Trách trở lên) Xem và duyệt báo cáo")
    @app_commands.describe(ma="Mã báo cáo; bỏ trống để xem danh sách", duyet="Đồng ý hay từ chối")
    @rate_limit(3)
    async def duyet(self, itx: discord.Interaction, ma: int | None = None, duyet: bool = True):
        if ma is None:
            rows = await self.call(itx, self.g.orgs.pending_reports, itx.user.id)
            if rows is not FAILED:
                await itx.response.send_message(embed=self.ui.reports(rows), ephemeral=True)
            return
        if await self.call(itx, self.g.orgs.review_report, itx.user.id, ma, duyet) is not FAILED:
            await self.done(itx, "Đã xử lý", f"Báo cáo `#{ma}` đã {'duyệt' if duyet else 'từ chối'}.", True)

    @to_chuc.command(name="thang_chuc", description="Thăng cấp cho thành viên (chỉ lên cấp thấp hơn cấp của bạn)")
    @app_commands.choices(cap=RANK_CH, khu_vuc=REGION_CH)
    @rate_limit(3)
    async def thang(self, itx: discord.Interaction, nguoi: discord.User, cap: app_commands.Choice[str] | None = None,
                    khu_vuc: app_commands.Choice[str] | None = None):
        r = await self.call(itx, self.g.orgs.promote, itx.user.id, nguoi.id, cap.value if cap else None,
                            khu_vuc.value if khu_vuc else None)
        if r is not FAILED:
            await self.done(itx, "Thăng chức", f"{nguoi.mention} nay là **{RANKS[r][1]}**.")

    @to_chuc.command(name="giang_chuc", description="Giáng một cấp cho người có cấp thấp hơn bạn")
    @rate_limit(3)
    async def giang(self, itx: discord.Interaction, nguoi: discord.User):
        r = await self.call(itx, self.g.orgs.demote, itx.user.id, nguoi.id)
        if r is not FAILED:
            await self.done(itx, "Giáng chức", f"{nguoi.mention} nay là **{RANKS[r][1]}**.")

    @to_chuc.command(name="loai", description="Loại thành viên cấp thấp hơn khỏi Tổng Bộ")
    @rate_limit(3)
    async def loai(self, itx: discord.Interaction, nguoi: discord.User):
        if await self.call(itx, self.g.orgs.kick, itx.user.id, nguoi.id) is not FAILED:
            await self.done(itx, "Đã loại", f"{nguoi.mention} không còn trong Tổng Bộ.")

    @to_chuc.command(name="khu_vuc", description="Điều động thành viên sang khu vực khác")
    @app_commands.choices(khu_vuc=REGION_CH)
    @rate_limit(3)
    async def khu_vuc(self, itx: discord.Interaction, nguoi: discord.User, khu_vuc: app_commands.Choice[str]):
        if await self.call(itx, self.g.orgs.set_region, itx.user.id, nguoi.id, khu_vuc.value) is not FAILED:
            await self.done(itx, "Điều động", f"{nguoi.mention} nay thuộc khu **{REGIONS[khu_vuc.value]}**.")

    @to_chuc.command(name="nop_quy", description="Đóng góp tiền cổ vào ngân quỹ, nhận danh tiếng và cống hiến")
    @rate_limit(3)
    async def nop_quy(self, itx: discord.Interaction, so_tien: app_commands.Range[int, 1, 100000]):
        if await self.call(itx, self.g.orgs.contribute, itx.user.id, so_tien) is not FAILED:
            await self.done(itx, "Cảm ơn", f"Đã nộp {so_tien} tiền cổ vào ngân quỹ.", True)

    @to_chuc.command(name="ho_so_linh_di", description="Hồ sơ linh dị: xem kho giam giữ hoặc đọc hồ sơ để nhận manh mối")
    @app_commands.choices(quy=[app_commands.Choice(name=g["name"], value=k) for k, g in GHOSTS.items()])
    @app_commands.describe(quy="Lệ quỷ cần đọc hồ sơ; bỏ trống để xem danh sách")
    @rate_limit(3)
    async def ho_so_linh_di(self, itx: discord.Interaction, quy: app_commands.Choice[str] | None = None):
        if quy is None:
            data = await self.call(itx, self.g.orgs.archive_list, itx.user.id)
            if data is not FAILED:
                await itx.response.send_message(embed=self.ui.archive(data), ephemeral=True)
            return
        r = await self.call(itx, self.g.orgs.read_archive, itx.user.id, quy.value)
        if r is not FAILED:
            await itx.response.send_message(embed=self.ui.archive_read(r), ephemeral=True)
            await self.flush(itx)

    @to_chuc.command(name="mo_phong_toa", description="(Người Phụ Trách trở lên) Tốn 150 ngân quỹ để tháo phong tỏa một khu")
    @app_commands.choices(dia_diem=LOC_CH)
    @rate_limit(5)
    async def mo_phong_toa(self, itx: discord.Interaction, dia_diem: app_commands.Choice[str]):
        if await self.call(itx, self.g.orgs.lift_lock, itx.user.id, dia_diem.value) is not FAILED:
            await self.done(itx, "Đã tháo phong tỏa", f"{dia_diem.name} mở cửa trở lại.")


async def setup(bot):
    await bot.add_cog(OrgCog(bot))

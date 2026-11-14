"""Vẽ toàn bộ emoji pixel art của game bằng Pillow.

Mỗi sprite là lưới 16x16, nền trong suốt, tự động viền tối, phóng 8x (nearest) thành PNG 128x128
(kích thước Discord khuyến nghị cho emoji tùy chỉnh). Chạy:  python tools/generate_emoji.py
Tạo: assets/emoji/<nhóm>/<tên>.png, assets/emoji/emoji_map.json, assets/emoji/_contact_sheet.png
Tất cả hình do dự án tự vẽ; không dùng tranh/ảnh nhân vật có bản quyền.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "emoji"
SCALE, N = 8, 16

# Bảng màu kinh dị u ám (tự chọn, tham khảo cách phối palette tối trên Lospec)
PAL = {
    "k": "#0d0b10", "d": "#2a2433", "e": "#3a3445", "g": "#5a5266", "l": "#a39bb0", "w": "#e8e2d4",
    "r": "#8e1b1b", "R": "#d12f2f", "q": "#ff7b6b", "o": "#c9822b", "y": "#e8c25a", "Y": "#fff0a0",
    "b": "#2d4a6b", "B": "#5b8bb5", "c": "#4f8f7c", "C": "#8fd6b8", "u": "#2f6b5a",
    "p": "#5b2f7a", "P": "#a56fd1", "v": "#c2a3ef", "n": "#4a2f1e", "N": "#8a5c36", "s": "#d8b8a0",
}


class Canvas:
    def __init__(self):
        self.px = [[None] * N for _ in range(N)]

    def set(self, x, y, c):
        if 0 <= x < N and 0 <= y < N:
            self.px[y][x] = c

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, c)

    def circle(self, cx, cy, r, c):
        for y in range(N):
            for x in range(N):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + r:
                    self.set(x, y, c)

    def ring(self, cx, cy, r0, r1, c):
        for y in range(N):
            for x in range(N):
                d = math.hypot(x - cx, y - cy)
                if r0 <= d <= r1:
                    self.set(x, y, c)

    def line(self, x0, y0, x1, y1, c):
        pts, dx, dy = [], abs(x1 - x0), -abs(y1 - y0)
        sx, sy, err = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1), dx + dy
        while True:
            pts.append((x0, y0))
            if (x0, y0) == (x1, y1):
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy
        for x, y in pts:
            self.set(x, y, c)
        return pts

    def rows(self, rows, sym):
        """Đặt lưới vùng 14x14 (có thể đối xứng) vào giữa khung 16x16."""
        h = len(rows)
        assert h <= 14, f"quá cao: {h}"
        y0 = 1 + (14 - h) // 2
        for j, row in enumerate(rows):
            if sym:
                assert len(row) == 7, f"hàng đối xứng phải dài 7: {row!r}"
                row = row + row[::-1]
            assert len(row) == 14, f"hàng phải dài 14: {row!r}"
            for i, ch in enumerate(row):
                if ch != ".":
                    self.set(1 + i, y0 + j, ch)

    def outline(self, c="k"):
        keep = [row[:] for row in self.px]
        for y in range(N):
            for x in range(N):
                if keep[y][x] is None and any(
                        0 <= x + dx < N and 0 <= y + dy < N and keep[y + dy][x + dx] is not None
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    self.px[y][x] = c

    def image(self):
        im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        for y in range(N):
            for x in range(N):
                c = self.px[y][x]
                if c:
                    im.putpixel((x, y), tuple(int(PAL[c][i:i + 2], 16) for i in (1, 3, 5)) + (255,))
        return im.resize((N * SCALE, N * SCALE), Image.NEAREST)


S = lambda rows: ("sym", rows)  # noqa: E731  lưới đối xứng (7 cột, soi gương)
F = lambda rows: ("full", rows)  # noqa: E731  lưới đầy đủ (14 cột)

SPRITES: dict[str, dict] = {}


def reg(name, cat, label, fallback, spec=None, draw=None, patch=(), raw=False):
    SPRITES[name] = dict(cat=cat, label=label, fallback=fallback, spec=spec, draw=draw, patch=patch, raw=raw)


# ======================================================================= LỆ QUỶ
reg("ghost_quy_thu", "le_quy", "Quỷ Thủ", "✋", F([
    ".......RR.....", ".......cc.....", ".......cc.....", "....RR.cc.RR..", "....cc.cc.cc..",
    ".RR.cc.cc.cc..", ".Cc.Cc.Cc.Cc..", ".Cc.Cc.Cc.Cc..", ".ccccccccccc..", ".ccccrrccccc..",
    ".cccccccccccc.", "..cccccccccc..", "...cccccccc...", "....cccccc....",
]))
reg("ghost_quy_anh", "le_quy", "Quỷ Ảnh", "👤", S([
    "...pppp", "..pppPP", ".pppppp", ".ppwwpp", ".ppwwpp", ".pppppp", "..ppppp", ".pppppp",
    "ppppppp", "pppdddd", "pppdddd", "ppppppp", "p.ppp.p", ".p.p.p.",
]))
reg("ghost_quy_nhan", "le_quy", "Quỷ Nhãn", "👁", S([
    "....ddd", "..ddwww", ".dwwwww", "dwrwRRR", "dwwRRkk", "dwwRRkk", "drwwRRR", ".dwwwww",
    "..ddwww", "....ddd", "......R", "......R",
]))
reg("ghost_quy_quan_tai", "le_quy", "Quỷ Quan Tài", "⚰", S([
    "...nnnn", "..nNNRR", ".nNNNNN", "nNNNNNN", "nNNNNNy", "nNNNNNy", "nNNNyyy", "nNNNNNy",
    "nNNNNNy", "nNNNNNy", ".nNNNNN", ".nNNNNN", "..nNNNN", "...nnnn",
]))
reg("ghost_quy_mon", "le_quy", "Quỷ Môn", "🚪", S([
    "rrrrrrr", ".rrrrrr", ".nnnnnn", ".nNNNyY", ".nNyNyY", ".nNNNyY", ".nNNNyY", ".nNyNyY",
    ".nNNNyY", ".nNNNyY", ".nNyNyY", ".nNNNyY", ".nnnnnY",
]))
reg("ghost_quy_vuc", "le_quy", "Quỷ Vực", "🌀", S([
    ".....pp", "...pppP", "..ppPPp", ".ppPppd", ".pPpddd", "ppPpddk", "pPpddkw", "pPpddkw",
    "ppPpddk", ".pPpddd", ".ppPppd", "..ppPPp", "...pppP", ".....pp",
]))

# ======================================================================= NHÂN VẬT
reg("char_ngu_quy_gia", "nhan_vat", "Ngự Quỷ Giả", "🧙", S([
    "...dddd", "..ddddd", "..dssss", "..dskss", "..dssss", "...RRRR", ".dddddd", "dddddcc",
    "dddddcc", "ddddddd", ".dddddd", ".ddddd.", ".ddddd.", ".kkkkk.",
]))
reg("char_nguoi_thuong", "nhan_vat", "Người Thường", "🙂", S([
    "...nnnn", "..nnnnn", "..nssss", "..nskss", "..nssss", "....sss", ".BBBBBB", "BBBBBBB",
    "BBBBBBB", "BBBBBBB", ".bbbbbb", ".bbbbb.", ".bbbbb.", ".kkkkk.",
]))
reg("char_nhiem_linh_di", "nhan_vat", "Nhiễm Linh Dị", "🧟", S([
    "...dddd", "..ddddd", "..dcccc", "..dcRcc", "..dcCcc", "....ccc", ".gggggg", "ggdgggg",
    "ggggdgg", "gdggggg", ".gggggg", ".gg.gg.", ".gg.gg.", ".kk.kk.",
]))
reg("char_mat_kiem_soat", "nhan_vat", "Mất Kiểm Soát", "😱", S([
    "..d.d.d", "..ddddd", "..dwwww", "..dkkww", "..dkkww", "..dwwww", "..dwkkk", "...wwww",
    "PPPPPPP", "..ddddd", "..dRRRR", "..ddddd", "..ddd..", "..ddd..",
]))

# ======================================================================= VẬT PHẨM
reg("item_linh_di_vat", "vat_pham", "Linh Dị Vật (Gương Nứt)", "🪞", S([
    "....yyy", "..yyyoo", ".yoBBBB", ".yBBBwB", "yoBBwBB", "yoBBBBB", "yoBBBBB", "yoBBBBB",
    "yoBBBBB", ".yBBBBB", ".yoBBBB", "..yyyyy", ".....nn", ".....nn",
]), patch=[(7, 4, "k"), (8, 5, "k"), (7, 6, "k"), (8, 7, "k"), (8, 8, "k"), (9, 9, "k")])
reg("item_quan_tai", "vat_pham", "Quan Tài", "⚰", S([
    "..nnnnn", ".nNNNNN", "nNNNNNN", "nNNNNNy", "nNNNNNy", "nNNNNNN", ".nNNNNN", "..nnnnn",
]))
reg("item_den_dau", "vat_pham", "Đèn Dầu", "🪔", S([
    "......Y", ".....oY", ".....oY", "....ooY", "...llwY", "...lwYY", "..lwYYY", "..lwYYY",
    "...lwYY", "..yyyyy", ".yooooo", ".yooooo", "..yyyyy", "..nnnnn",
]))
reg("item_tien_co", "vat_pham", "Tiền Cổ", "🪙", S([
    "....ooy", "..oyyyy", ".oYyyyy", ".oyyyyy", "oyyyyyy", "oyyyykk", "oyyyykk", "oyyyykk",
    "oyyyykk", "oyyyyyy", ".oyyyyy", ".oyyyyy", "..oyyyy", "....ooy",
]))
reg("item_thu_linh_di", "vat_pham", "Thư Linh Dị", "✉", S([
    "wwwwwww", "wlwwwww", "wwlwwww", "wwwlwRR", "wwwwlRR", "wwwwwRR", "wwwwwww", "wwwwwww",
    "wwwwwww", "ggggggg",
]))
reg("item_vat_phong_an", "vat_pham", "Vật Chứa Vàng (Phong Ấn)", "🏺", S([
    "..yyyyy", ".yYYYYY", ".yyyyyy", "..oyyww", "..oyywR", "..oyywR", "..oyywR", "..oyywR",
    "..oyywR", "..oyyww", "..ooooo", ".oooooo",
]))
reg("item_hinh_nhan", "vat_pham", "Hình Nhân Thế Mạng", "🧍", S([
    "...wwww", "..wwwww", "..wkwww", "..wRwww", "...wwww", "wwwwwww", "wwwwwww", "...wwww",
    "...wwww", "...wlww", "..wwwww", "..www..", "..www..", "..www..",
]))

# ======================================================================= GIAO DIỆN
reg("ui_sinh_ton", "giao_dien", "Sinh Tồn", "❤", S([
    ".RRRR..", "RRwRRRR", "RRRRRRR", "RRRRRRR", ".RRRRRR", "..RRRRR", "...rRRR", "....rRR",
    ".....rR", "......r",
]))
reg("ui_nguy_hiem", "giao_dien", "Nguy Hiểm", "⚠", S([
    "......y", ".....yy", ".....yy", "....yyk", "...yyyk", "...yyyk", "..yyyyk", "..yyyyk",
    ".yyyyyy", ".yyyyyk", "yyyyyyy", "yyyyyyy", "ooooooo",
]))
reg("ui_nhiem_vu", "giao_dien", "Nhiệm Vụ", "📜", S([
    "NNNNNNN", ".wwwwww", ".wggggg", ".wwwwww", ".wggggg", ".wwwwRR", ".wwwwRR", ".wggggg",
    ".wwwwww", "NNNNNNN",
]))
reg("ui_phong_an", "giao_dien", "Phong Ấn", "🔒", S([
    "....ooo", "....yyy", "....yRR", "....RyR", "nnnnnnn", "....RRR", "....yRy", "....RyR",
    "nnnnnnn", "....yRR", "....yyy", "....ooo",
]))


def _kham_pha(c):
    c.circle(6, 6, 4, "B")
    c.ring(6, 6, 3.6, 5.0, "y")
    for x, y in ((4, 4), (5, 4), (4, 5)):
        c.set(x, y, "w")
    for off in (0, 1):
        for x, y in c.line(10, 10, 13, 13, "n"):
            c.set(x + off, y, "n")


def _sword(c, x0, y0, x1, y1):
    pts = c.line(x0, y0, x1, y1, "l")
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        if i < n // 3:
            c.set(x, y, "N")
        elif i % 2 == 0:
            c.set(x, y, "w")
    gx, gy = pts[n // 3]
    sx = 1 if (x1 - x0) * (y1 - y0) < 0 else -1  # hướng vuông góc
    for k in range(-2, 3):
        c.set(gx + k, gy + k * sx, "y")


def _chien_dau(c):
    _sword(c, 2, 13, 13, 2)
    _sword(c, 13, 13, 2, 2)


def _thanh_cong(c):
    c.circle(8, 8, 6, "c")
    c.ring(8, 8, 5.2, 6.6, "C")
    for x, y in c.line(5, 8, 7, 10, "w") + c.line(7, 10, 11, 5, "w"):
        c.set(x + 1, y, "w")


def _that_bai(c):
    c.circle(8, 8, 6, "r")
    c.ring(8, 8, 5.2, 6.6, "R")
    for x, y in c.line(5, 5, 11, 11, "w") + c.line(11, 5, 5, 11, "w"):
        c.set(x + 1, y, "w")


reg("ui_kham_pha", "giao_dien", "Khám Phá", "🔍", draw=_kham_pha)
reg("ui_chien_dau", "giao_dien", "Chiến Đấu", "⚔", draw=_chien_dau)
reg("ui_thanh_cong", "giao_dien", "Thành Công", "✅", draw=_thanh_cong)
reg("ui_that_bai", "giao_dien", "Thất Bại", "❌", draw=_that_bai)

# ======================================================================= ĐỊA ĐIỂM
reg("loc_benh_vien", "dia_diem", "Bệnh Viện", "🏥", S([
    "ggggggg", "wwwwwww", "wwwwwwR", "wwwwwwR", "wwwwRRR", "wwwwRRR", "wwwwwwR", "wwwwwwR",
    "wBBwBBw", "wBBwBBw", "wwwwddd", "ggggggg",
]))
reg("loc_truong_hoc", "dia_diem", "Trường Học", "🏫", S([
    "......r", ".....rr", "....rrr", "....wwk", "....wwk", "....nnn", ".rrrrrr", "NNNNNNN",
    "NBBNBBN", "NBBNBBN", "NNNNddd", "ggggggg",
]))
reg("loc_nghia_trang", "dia_diem", "Nghĩa Trang", "🪦", S([
    "...gggg", "..ggggg", ".ggllll", ".gglllk", ".gglkkk", ".gglllk", ".gglllk", ".gglllk",
    ".ggllll", ".ggllll", "cdcdcdc", "ddddddd",
]))
reg("loc_lang_hoang", "dia_diem", "Làng Bỏ Hoang", "🏚", S([
    "......n", ".....nn", "....ndd", "...nnnd", "..nnnnn", ".nnnnnn", ".NNNNNN", ".NdNNNN",
    ".NdNNdd", ".NNNNdd", ".NNNNdd", "ccgcgcc",
]))
reg("loc_khu_dan_cu", "dia_diem", "Khu Dân Cư", "🏢", S([
    "ggggggg", "gddgddg", "gddgddg", "ggggggg", "gddgddg", "gddgddg", "ggggggg", "gddgddg",
    "gddgddg", "ggggggg", "gddgddg", "gddgddg", "ggggddd", "ggggddd",
]), patch=[(2, 5, "Y"), (3, 5, "Y"), (2, 6, "Y"), (3, 6, "Y"), (9, 8, "o"), (10, 8, "o"), (9, 9, "o"), (10, 9, "o")])


def _thanh_pho(c):
    c.circle(13, 2, 1, "w")                       # trăng
    c.rect(1, 8, 3, 13, "g")                      # nhà trái
    c.rect(12, 8, 14, 13, "g")                    # nhà phải
    for x, y, col in ((2, 9, "Y"), (2, 11, "d"), (13, 10, "d"), (13, 12, "Y")):
        c.set(x, y, col)
    c.rect(7, 1, 8, 1, "r")                       # tháp ba tầng
    c.rect(6, 2, 9, 2, "r")
    c.rect(7, 3, 8, 4, "n")
    c.rect(5, 5, 10, 5, "r")
    c.rect(6, 6, 9, 8, "n")
    c.rect(5, 9, 10, 9, "r")
    c.rect(6, 10, 9, 13, "n")
    c.rect(7, 11, 8, 13, "o")
    c.set(7, 7, "Y")
    c.set(8, 7, "Y")


reg("loc_thanh_pho", "dia_diem", "Thành Phố", "🏙", draw=_thanh_pho)


# ======================================================================= THANH TIẾN ĐỘ (xếp liền không viền)
def _bar(base, top, bottom):
    def draw(c):
        c.rect(0, 4, 15, 11, base)
        c.rect(0, 4, 15, 5, top)
        c.rect(0, 10, 15, 11, bottom)
    return draw


reg("bar_hp", "thanh_tien_do", "Thanh Thể Chất", "🟥", draw=_bar("R", "q", "r"), raw=True)
reg("bar_mind", "thanh_tien_do", "Thanh Tinh Thần", "🟪", draw=_bar("P", "v", "p"), raw=True)
reg("bar_ghost", "thanh_tien_do", "Thanh Phục Tô", "🟩", draw=_bar("c", "C", "u"), raw=True)
reg("bar_empty", "thanh_tien_do", "Thanh Rỗng", "⬛", draw=_bar("d", "e", "k"), raw=True)


def render(name) -> Image.Image:
    s = SPRITES[name]
    c = Canvas()
    if s["spec"]:
        mode, rows = s["spec"]
        c.rows(rows, mode == "sym")
    if s["draw"]:
        s["draw"](c)
    for x, y, col in s["patch"]:
        c.set(x, y, col)
    if not s["raw"]:
        c.outline()
    return c.image()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mapping = {"version": 1, "size": N * SCALE, "emoji": {}}
    imgs = []
    for name, s in SPRITES.items():
        d = OUT / s["cat"]
        d.mkdir(exist_ok=True)
        im = render(name)
        im.save(d / f"{name}.png", optimize=True)
        mapping["emoji"][name] = {"file": f"{s['cat']}/{name}.png", "category": s["cat"], "label": s["label"],
                                  "fallback": s["fallback"]}
        imgs.append((name, im))
    (OUT / "emoji_map.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    cols = 8
    rows = math.ceil(len(imgs) / cols)
    cell = 128 + 12
    sheet = Image.new("RGBA", (cols * cell, rows * cell), (54, 57, 63, 255))  # nền giống Discord tối
    for i, (_, im) in enumerate(imgs):
        sheet.alpha_composite(im, ((i % cols) * cell + 6, (i // cols) * cell + 6))
    sheet.save(OUT / "_contact_sheet.png")
    print(f"Đã vẽ {len(imgs)} emoji -> {OUT}")


if __name__ == "__main__":
    sys.exit(main())

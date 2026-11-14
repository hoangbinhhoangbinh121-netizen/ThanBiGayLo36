"""Nhất quán tài nguyên: mọi emoji được mã tham chiếu đều tồn tại, mọi PNG hợp lệ theo giới hạn của Discord."""
import ast
import json
import re
import struct
import unittest
from pathlib import Path

from tests.helpers import ROOT

EMOJI = ROOT / "assets" / "emoji"
PREFIX = re.compile(r"^(ghost|char|item|ui|loc|bar)_[a-z_]+$")
# Chuỗi trùng tiền tố nhưng KHÔNG phải emoji: tên cột DB / khóa dữ liệu / loại sự kiện trên bus
NOT_EMOJI = {"ghost_id", "ghost_instance_id", "item_id", "ghost_sealed", "item_gained"}


def png_info(path: Path):
    b = path.read_bytes()
    assert b[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} không phải PNG"
    w, h, depth, ctype = struct.unpack(">IIBB", b[16:26])
    return w, h, ctype, len(b)


class EmojiAssetTests(unittest.TestCase):
    def setUp(self):
        self.map = json.loads((EMOJI / "emoji_map.json").read_text(encoding="utf-8"))["emoji"]

    def test_map_and_files_match_exactly(self):
        files = {p.stem for p in EMOJI.glob("*/*.png")}
        self.assertEqual(set(self.map), files)
        self.assertEqual(len(self.map), 35)
        for name, info in self.map.items():
            self.assertTrue((EMOJI / info["file"]).exists(), name)
            self.assertEqual(info["file"].split("/")[0], info["category"])
            self.assertTrue(info["fallback"] and info["label"])

    def test_every_png_fits_discord_limits(self):
        for name in self.map:
            w, h, ctype, size = png_info(EMOJI / self.map[name]["file"])
            self.assertEqual((w, h), (128, 128), name)        # kích thước Discord khuyến nghị
            self.assertEqual(ctype, 6, f"{name} phải là RGBA")  # PNG 8-bit RGBA = có kênh trong suốt
            self.assertLessEqual(size, 256 * 1024, name)
            self.assertRegex(name, r"^[A-Za-z0-9_]{2,32}$")

    def test_all_emoji_names_used_in_code_exist(self):
        """Gõ sai tên emoji sẽ cho ra chuỗi rỗng âm thầm; quét toàn bộ mã nguồn để bắt lỗi chính tả."""
        used = {}
        for path in list(ROOT.glob("*.py")) + [p for d in ("core", "engine", "data", "cogs") for p in (ROOT / d).glob("*.py")]:
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (isinstance(node, ast.Constant) and isinstance(node.value, str) and PREFIX.match(node.value)
                        and node.value not in NOT_EMOJI):
                    used.setdefault(node.value, path.name)
        missing = {n: f for n, f in used.items() if n not in self.map}
        self.assertEqual(missing, {})
        self.assertGreater(len(used), 25)

    def test_emoji_cover_every_required_group_of_the_spec(self):
        need = {"ghost_quy_thu", "ghost_quy_anh", "ghost_quy_nhan", "ghost_quy_quan_tai", "ghost_quy_mon", "ghost_quy_vuc",
                "char_ngu_quy_gia", "char_nguoi_thuong", "char_nhiem_linh_di", "char_mat_kiem_soat",
                "item_linh_di_vat", "item_quan_tai", "item_den_dau", "item_tien_co", "item_thu_linh_di", "item_vat_phong_an",
                "ui_sinh_ton", "ui_nguy_hiem", "ui_kham_pha", "ui_nhiem_vu", "ui_chien_dau", "ui_thanh_cong",
                "ui_that_bai", "ui_phong_an"}
        self.assertEqual(need - set(self.map), set())

    def test_sprites_are_deterministic(self):
        """Chạy lại bộ vẽ phải cho đúng các byte hiện có (kết quả tái lập được)."""
        import io
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        import generate_emoji as gen
        for name in ("ghost_quy_mon", "ui_phong_an", "bar_hp"):
            buf = io.BytesIO()
            gen.render(name).save(buf, format="PNG", optimize=True)
            self.assertEqual(buf.getvalue(), (EMOJI / self.map[name]["file"]).read_bytes(), name)


if __name__ == "__main__":
    unittest.main()

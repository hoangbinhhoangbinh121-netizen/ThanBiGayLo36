"""Tạo/nâng cấp cơ sở dữ liệu theo migration và sinh docs/DATABASE.md. Dùng: python tools/init_db.py [đường_dẫn_db]"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.database import Database  # noqa: E402


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "storage" / "than_bi_phuc_to.db"
    db = Database(path).connect()
    applied = db.migrate(ROOT / "migrations")
    print("Migration đã áp:", applied or "không có (đã mới nhất)", "| phiên bản:", db.schema_version())
    tables = [r["name"] for r in db.all("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    out = ["# Cơ sở dữ liệu", "", f"SQLite, {len(tables)} bảng, phiên bản schema {db.schema_version()}. Khóa ngoại bật (`PRAGMA foreign_keys=ON`), "
           "ràng buộc CHECK ở mức DB (chỉ số không âm, trạng thái hợp lệ, quỷ tự do không có chủ...).", "",
           "Quan hệ chính: `players` là gốc; hầu hết bảng tham chiếu `players(user_id)` với `ON DELETE CASCADE`. "
           "`ghost_instances` tham chiếu chủ sở hữu; `encounters`, `world_events`, `org_*`, `trades`, `quests`... nối vào cả hai.", ""]
    for t in tables:
        cols = db.all(f"PRAGMA table_info({t})")
        fks = db.all(f"PRAGMA foreign_key_list({t})")
        out.append(f"## `{t}`")
        out.append("Cột: " + ", ".join(f"`{c['name']}`" + (" (PK)" if c["pk"] else "") for c in cols))
        if fks:
            out.append("")
            out.append("Khóa ngoại: " + ", ".join(f"`{f['from']}` → `{f['table']}.{f['to']}` ({f['on_delete']})" for f in fks))
        out.append("")
    (ROOT / "docs" / "DATABASE.md").write_text("\n".join(out), encoding="utf-8")
    db.close()


if __name__ == "__main__":
    main()

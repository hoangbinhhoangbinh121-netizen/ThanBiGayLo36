"""Sinh COMMANDS.md từ cây lệnh THẬT của bot (tránh tài liệu lệch với mã).
Dùng bộ giả lập tests/fake_discord.py để đọc cấu trúc lệnh khi không cần kết nối Discord."""
import asyncio
import inspect
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tests import fake_discord  # noqa: E402

fake_discord.install()
import bot as botmod  # noqa: E402
from core.config import Config  # noqa: E402


def params(cmd):
    cb, out = cmd.callback, []
    desc, ch = getattr(cb, "__describe__", {}), getattr(cb, "__choices__", {})
    for p in list(inspect.signature(cb).parameters.values())[2:]:
        opt = p.default is not inspect.Parameter.empty
        s = f"`{p.name}`" + ("" if opt else "*")
        extra = desc.get(p.name, "")
        if p.name in ch:
            extra += (" " if extra else "") + "[" + " / ".join(c.name for c in ch[p.name][:8]) + ("…" if len(ch[p.name]) > 8 else "") + "]"
        out.append(s + (f" — {extra}" if extra else ""))
    return "<br>".join(out) or "—"


async def main():
    tmp = tempfile.mkdtemp()
    bot = botmod.TBPTBot(Config(db_path=str(Path(tmp) / "d.db"), auto_upload_emoji=False, emoji_upload_delay=0.0))
    await bot.setup_hook()
    lines = ["# Danh sách lệnh — Thần Bí Phục Tô", "",
             "Sinh tự động bằng `python tools/gen_docs.py` từ cây lệnh thật. Dấu * = tham số bắt buộc.", ""]
    n = 0
    for item in sorted(bot.tree.get_commands(), key=lambda i: i.name):
        if hasattr(item, "commands"):
            lines += [f"## /{item.name} — {item.description}", "", "| Lệnh | Tham số | Mô tả |", "|---|---|---|"]
            for c in sorted(item.commands, key=lambda c: c.name):
                lines.append(f"| `/{item.name} {c.name}` | {params(c)} | {c.description} |")
                n += 1
            lines.append("")
        else:
            lines.append(f"- `/{item.name}` — {item.description}" + (f"  \n  Tham số: {params(item)}" if params(item) != "—" else ""))
            n += 1
    lines.append("")
    lines.append(f"Tổng cộng {n} lệnh.")
    (ROOT / "COMMANDS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    await bot.close()
    print(f"COMMANDS.md: {n} lệnh")


asyncio.run(main())

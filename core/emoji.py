"""Sổ đăng ký emoji pixel art: đọc emoji_map.json, đồng bộ lên Discord (emoji ứng dụng), ghi ID vào DB."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path

log = logging.getLogger("tbpt.emoji")
NAME_RE = re.compile(r"^[A-Za-z0-9_]{2,32}$")
MAX_BYTES = 256 * 1024        # giới hạn emoji của Discord (256 KiB)
MAX_APP_EMOJIS = 2000         # giới hạn emoji ứng dụng


class EmojiRegistry:
    def __init__(self, emoji_dir, delay: float = 0.3):
        self.delay = delay
        self.dir = Path(emoji_dir)
        self.map: dict = json.loads((self.dir / "emoji_map.json").read_text(encoding="utf-8"))["emoji"]
        self.ids: dict[str, int] = {}

    # ---- tra cứu ---------------------------------------------------------------
    def load_ids(self, db):
        self.ids = {r["name"]: r["discord_id"] for r in db.all("SELECT name,discord_id FROM emoji_registry")}

    def uploaded(self) -> int:
        return sum(1 for n in self.map if n in self.ids)

    def fmt(self, name: str) -> str:
        """Chuỗi dùng trong Embed. Chưa tải lên Discord thì tạm dùng ký tự dự phòng (chỉ trước khi đồng bộ)."""
        if name in self.ids:
            return f"<:{name}:{self.ids[name]}>"
        return self.map.get(name, {}).get("fallback", "")

    def partial(self, name: str):
        """PartialEmoji cho Button / SelectOption; None nếu chưa tải lên."""
        import discord
        return discord.PartialEmoji(name=name, id=self.ids[name]) if name in self.ids else None

    def path(self, name: str) -> Path:
        return self.dir / self.map[name]["file"]

    # ---- đồng bộ -------------------------------------------------------------------
    async def sync(self, bot) -> tuple[int, int]:
        """Tải các emoji còn thiếu lên làm emoji ứng dụng (cần discord.py >= 2.5). Trả (mới tạo, tổng)."""
        existing = {e.name: e for e in await bot.fetch_application_emojis()}
        created = 0
        for name, info in self.map.items():
            emoji = existing.get(name)
            if emoji is None:
                data = (self.dir / info["file"]).read_bytes()
                if not NAME_RE.match(name) or len(data) > MAX_BYTES or data[:8] != b"\x89PNG\r\n\x1a\n":
                    raise ValueError(f"Emoji {name!r} không hợp lệ (tên 2-32 ký tự chữ-số-gạch dưới, PNG, <= 256 KiB)")
                if len(existing) + created >= MAX_APP_EMOJIS:
                    raise ValueError("Đã chạm giới hạn 2000 emoji ứng dụng")
                emoji = await bot.create_application_emoji(name=name, image=data)
                created += 1
                if self.delay:
                    await asyncio.sleep(self.delay)   # route emoji có giới hạn tốc độ riêng
            self.ids[name] = emoji.id
            bot.db.run("INSERT INTO emoji_registry(name,discord_id,uploaded_at) VALUES(?,?,?) "
                       "ON CONFLICT(name) DO UPDATE SET discord_id=excluded.discord_id",
                       (name, emoji.id, bot.game.clock.now()))
        log.info("Emoji: %d mới, %d tổng", created, len(self.map))
        return created, len(self.map)

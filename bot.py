"""Thần Bí Phục Tô - Bot By Tuyệt Thiên. Điểm khởi động: python bot.py"""
from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from core.config import ensure_env_template, load_config
from core.cooldown import Limiter
from core.database import Database
from core.emoji import EmojiRegistry
from core.guards import NotAdmin, RateLimited
from core.render import UI
from engine.game import Game

ROOT = Path(__file__).resolve().parent
EXTENSIONS = ["cogs.character", "cogs.world", "cogs.explore", "cogs.ghosts", "cogs.items", "cogs.org", "cogs.events",
              "cogs.admin"]
log = logging.getLogger("tbpt")


class TBPTBot(commands.Bot):
    def __init__(self, cfg):
        super().__init__(command_prefix=commands.when_mentioned, intents=discord.Intents.default(), help_command=None)
        self.cfg = cfg
        self.limiter = Limiter()
        self.db: Database | None = None
        self.game: Game | None = None
        self.emoji_reg: EmojiRegistry | None = None
        self.ui: UI | None = None

    async def setup_hook(self):
        self.db = Database(ROOT / self.cfg.db_path).connect()
        applied = self.db.migrate(ROOT / "migrations")
        if applied:
            log.info("Đã áp migration: %s", ", ".join(applied))
        self.game = Game(self.db)
        self.emoji_reg = EmojiRegistry(ROOT / "assets" / "emoji", self.cfg.emoji_upload_delay)
        self.emoji_reg.load_ids(self.db)
        if self.cfg.auto_upload_emoji:
            try:
                await self.emoji_reg.sync(self)
            except Exception:
                log.exception("Không đồng bộ được emoji (cần discord.py >= 2.5). Giao diện tạm dùng ký tự dự phòng.")
        self.ui = UI(self.emoji_reg)
        for ext in EXTENSIONS:
            await self.load_extension(ext)
        self.tree.on_error = self.on_tree_error
        if self.cfg.guild_id:
            guild = discord.Object(self.cfg.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def on_ready(self):
        log.info("Đã đăng nhập: %s (%s lệnh)", self.user, len(self.tree.get_commands()))

    async def on_tree_error(self, itx: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, (RateLimited, NotAdmin)):
            msg = str(error)
        elif isinstance(error, app_commands.CheckFailure):
            msg = "Bạn không đủ điều kiện dùng lệnh này."
        else:
            log.exception("Lỗi lệnh %s", getattr(itx.command, "qualified_name", "?"), exc_info=error)
            msg = "Có điều gì đó trong bóng tối đã làm hỏng lệnh này. Lỗi đã được ghi lại."
        embed = self.ui.error(msg) if self.ui else discord.Embed(description=msg)
        try:
            if itx.response.is_done():
                await itx.followup.send(embed=embed, ephemeral=True)
            else:
                await itx.response.send_message(embed=embed, ephemeral=True)
        except discord.HTTPException:
            pass

    async def close(self):
        await super().close()
        if self.db:
            self.db.close()


def main():
    if ensure_env_template(ROOT):
        print("Đã tạo file .env ở thư mục gốc. Mở nó ra, điền DISCORD_TOKEN rồi Start lại.")
    cfg = load_config(str(ROOT / "config.json"))
    log_dir = ROOT / cfg.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(log_dir / "tbpt.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")])
    if not cfg.token:
        print("Thiếu token. Mở file .env ở thư mục gốc, điền DISCORD_TOKEN=... rồi Start lại.")
        return 1
    TBPTBot(cfg).run(cfg.token, log_handler=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())

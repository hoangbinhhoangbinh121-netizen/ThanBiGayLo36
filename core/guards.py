"""Chống spam và kiểm tra quyền cho lệnh slash."""
from __future__ import annotations

from discord import app_commands


class RateLimited(app_commands.CheckFailure):
    pass


class NotAdmin(app_commands.CheckFailure):
    pass


def rate_limit(seconds: float = 2.0, bucket: str | None = None):
    """Mỗi người dùng chỉ được gọi lệnh này mỗi `seconds` giây; bắn liên tục sẽ bị chặn tạm."""
    def decorator(func):
        name = bucket or func.__name__

        async def predicate(interaction):
            ok, wait = interaction.client.limiter.hit(interaction.user.id, name, seconds)
            if not ok:
                raise RateLimited(f"Chậm lại một chút. Thử lại sau {wait:.0f} giây.")
            return True
        return app_commands.check(predicate)(func)
    return decorator


def is_admin(interaction) -> bool:
    cfg = interaction.client.cfg
    if interaction.user.id in cfg.owner_ids:
        return True
    perms = getattr(interaction.user, "guild_permissions", None)
    return bool(perms and perms.administrator)


def admin_only():
    async def predicate(interaction):
        if not is_admin(interaction):
            raise NotAdmin("Lệnh này chỉ dành cho quản trị viên của bot.")
        return True
    return app_commands.check(predicate)

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

ENV_TEMPLATE = """# Điền thông tin vào sau dấu = (không dùng dấu ngoặc kép, không để khoảng trắng).
# Token bot Discord (lấy ở Discord Developer Portal > Bot > Reset Token)
DISCORD_TOKEN=
# ID Discord của chủ bot, nhiều người thì cách nhau bằng dấu phẩy. Ví dụ: 123456789012345678,987654321098765432
TBPT_OWNER_IDS=
"""


@dataclass
class Config:
    token: str = ""
    owner_ids: list = field(default_factory=list)
    db_path: str = "storage/than_bi_phuc_to.db"
    backup_dir: str = "backups"
    backup_keep: int = 7
    backup_interval_hours: int = 6
    guild_id: int | None = None
    auto_upload_emoji: bool = True
    emoji_upload_delay: float = 0.3   # giãn cách giữa các lần tải emoji (Discord giới hạn riêng cho route emoji)
    log_dir: str = "logs"
    tick_seconds: int = 60


def ensure_env_template(root) -> bool:
    """Tạo file .env mẫu nếu chưa có. Trả về True nếu vừa tạo."""
    p = Path(root) / ".env"
    if p.exists():
        return False
    p.write_text(ENV_TEMPLATE, encoding="utf-8")
    return True


def _load_env_file(p: Path) -> None:
    """Đọc .env đơn giản (KEY=VALUE). Biến môi trường đặt từ panel host được ưu tiên nếu đã có giá trị."""
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and not os.environ.get(k):
            os.environ[k] = v


def load_config(path: str = "config.json") -> Config:
    cfg = Config()
    p = Path(path)
    if p.exists():
        try:
            raw = json.loads(p.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as e:
            print(f"[cảnh báo] config.json sai cú pháp JSON ({e}). Bỏ qua file này; "
                  "hãy xoá nó và điền token vào file .env thay thế.")
            raw = {}
        for k, v in raw.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
    _load_env_file(p.parent / ".env")
    cfg.token = os.environ.get("DISCORD_TOKEN", cfg.token)
    if os.environ.get("TBPT_OWNER_IDS"):
        cfg.owner_ids = [int(x) for x in os.environ["TBPT_OWNER_IDS"].split(",") if x.strip()]
    return cfg

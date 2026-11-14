"""SQLite layer: giao dịch lồng nhau (savepoint), migration có phiên bản, sao lưu an toàn."""
from __future__ import annotations

import asyncio
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path


class Database:
    def __init__(self, path, clock=None):
        self.path = str(path)
        self.clock = clock
        self._lock = threading.RLock()
        self._depth = 0
        self.conn: sqlite3.Connection | None = None

    # ---- kết nối -------------------------------------------------------
    def connect(self) -> "Database":
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA busy_timeout=5000")
        if self.path != ":memory:":
            self.conn.execute("PRAGMA journal_mode=WAL")
        return self

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def _now(self) -> int:
        return self.clock.now() if self.clock else int(time.time())

    # ---- giao dịch -----------------------------------------------------
    @contextmanager
    def tx(self):
        """Giao dịch ngoài cùng = BEGIN IMMEDIATE; giao dịch lồng = SAVEPOINT."""
        with self._lock:
            name = f"sp{self._depth}"
            self.conn.execute("BEGIN IMMEDIATE" if self._depth == 0 else f"SAVEPOINT {name}")
            self._depth += 1
            try:
                yield self
            except BaseException:
                self._depth -= 1
                if self._depth == 0:
                    self.conn.execute("ROLLBACK")
                else:
                    self.conn.execute(f"ROLLBACK TO {name}")
                    self.conn.execute(f"RELEASE {name}")
                raise
            else:
                self._depth -= 1
                self.conn.execute("COMMIT" if self._depth == 0 else f"RELEASE {name}")

    def one(self, sql, params=()):
        with self._lock:
            return self.conn.execute(sql, params).fetchone()

    def all(self, sql, params=()):
        with self._lock:
            return self.conn.execute(sql, params).fetchall()

    def run(self, sql, params=()):
        with self._lock:
            return self.conn.execute(sql, params)

    def scalar(self, sql, params=(), default=None):
        r = self.one(sql, params)
        return default if r is None or r[0] is None else r[0]

    # ---- migration -----------------------------------------------------
    def migrate(self, folder) -> list[str]:
        """Áp các file NNN_ten.sql chưa chạy. Mỗi file chạy trong một giao dịch riêng."""
        folder = Path(folder)
        applied: list[str] = []
        with self._lock:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations("
                "version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at INTEGER NOT NULL)"
            )
            done = {r["version"] for r in self.conn.execute("SELECT version FROM schema_migrations")}
            for f in sorted(folder.glob("[0-9][0-9][0-9]_*.sql")):
                version = int(f.name[:3])
                if version in done:
                    continue
                sql = f.read_text(encoding="utf-8")
                script = (
                    f"BEGIN;\n{sql}\n"
                    f"INSERT INTO schema_migrations(version,name,applied_at) "
                    f"VALUES({version},'{f.stem}',{self._now()});\nCOMMIT;"
                )
                try:
                    self.conn.executescript(script)
                except Exception:
                    if self.conn.in_transaction:
                        self.conn.execute("ROLLBACK")
                    raise
                applied.append(f.name)
        return applied

    def schema_version(self) -> int:
        return int(self.scalar("SELECT MAX(version) FROM schema_migrations", default=0))

    # ---- sao lưu -------------------------------------------------------
    def backup(self, dest_dir, keep: int = 7) -> Path:
        """Sao lưu nóng bằng SQLite backup API (an toàn khi bot đang chạy), giữ `keep` bản mới nhất."""
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime(self._now()))
        target = dest / f"tbpt-{stamp}.db"
        n = 1
        while target.exists():
            target = dest / f"tbpt-{stamp}-{n}.db"
            n += 1
        with self._lock:
            out = sqlite3.connect(str(target))
            try:
                self.conn.backup(out)
            finally:
                out.close()
        files = sorted(dest.glob("tbpt-*.db"), key=lambda f: (f.stat().st_mtime_ns, f.name))
        for old in files[:-keep] if keep > 0 else []:
            old.unlink()
        return target

    # ---- async ---------------------------------------------------------
    async def call(self, fn, *args, **kwargs):
        """Chạy hàm đồng bộ của engine trong thread, giữ khóa DB suốt cả lời gọi."""
        return await asyncio.to_thread(self._guarded, fn, args, kwargs)

    def _guarded(self, fn, args, kwargs):
        with self._lock:
            return fn(*args, **kwargs)

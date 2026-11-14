"""Chống spam: giới hạn tốc độ theo từng lệnh + chặn tạm khi bắn liên tục."""
import time
from collections import defaultdict, deque


class Limiter:
    def __init__(self, burst=14, window=20.0, block=30.0, now=time.monotonic):
        self.burst, self.window, self.block, self.now = burst, window, block, now
        self._last = {}
        self._hist = defaultdict(deque)
        self._blocked = {}
        self._n = 0

    def _prune(self, t):
        """Dọn các mục cũ để bộ nhớ không phình theo số người dùng đã từng gọi lệnh."""
        horizon = t - 3600
        self._last = {k: v for k, v in self._last.items() if v > horizon}
        for uid in [u for u, h in self._hist.items() if not h or t - h[-1] > self.window]:
            del self._hist[uid]
        self._blocked = {u: b for u, b in self._blocked.items() if b > t}

    def hit(self, user_id: int, bucket: str, seconds: float):
        """Trả (được_phép, số_giây_phải_chờ)."""
        t = self.now()
        self._n += 1
        if self._n % 500 == 0:
            self._prune(t)
        until = self._blocked.get(user_id, 0)
        if t < until:
            return False, until - t
        h = self._hist[user_id]
        while h and t - h[0] > self.window:
            h.popleft()
        h.append(t)
        if len(h) > self.burst:
            self._blocked[user_id] = t + self.block
            h.clear()
            return False, self.block
        key = (user_id, bucket)
        wait = self._last.get(key, 0) + seconds - t
        if wait > 0:
            return False, wait
        self._last[key] = t
        return True, 0.0

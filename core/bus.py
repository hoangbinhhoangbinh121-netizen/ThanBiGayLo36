class EventBus:
    """Bus đồng bộ: mọi hệ thống phát sự kiện, nhiệm vụ/thành tựu/thống kê lắng nghe.
    Chạy trong cùng giao dịch DB nên dữ liệu luôn nhất quán."""

    def __init__(self):
        self._subs = []

    def subscribe(self, fn):
        self._subs.append(fn)

    def emit(self, kind: str, user_id: int | None, **data):
        for fn in list(self._subs):
            fn(kind, user_id, data)

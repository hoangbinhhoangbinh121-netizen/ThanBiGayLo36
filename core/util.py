def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def wchoice(rng, weights: dict):
    """Chọn khóa theo trọng số (bỏ qua trọng số <= 0). Trả None nếu rỗng."""
    items = [(k, w) for k, w in weights.items() if w > 0]
    if not items:
        return None
    r = rng.uniform(0, sum(w for _, w in items))
    acc = 0.0
    for k, w in items:
        acc += w
        if r <= acc:
            return k
    return items[-1][0]


def fmt_dur(sec: int) -> str:
    sec = max(0, int(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}g{m:02d}p"
    if m:
        return f"{m}p{s:02d}s"
    return f"{s}s"

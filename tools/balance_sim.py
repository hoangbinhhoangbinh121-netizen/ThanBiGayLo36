"""Mô phỏng cân bằng đối mặt: tỷ lệ sống sót khi (a) không biết quy luật, chọn ngẫu nhiên; (b) biết đủ manh mối, chơi đúng.
Chạy: python tools/balance_sim.py [số_lần]   (dùng engine thuần, không cần Discord)"""
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.mechanics import MECHANICS  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
HAS_NONE = lambda i: False  # noqa: E731


def play(mech, rng, policy, known):
    st, p = mech.start(rng), {"sanity": 100, "hp": 100}
    hp = san = 0
    for _ in range(60):
        scene = mech.scene(st, known, HAS_NONE)
        opt = policy(mech, st, scene, rng)
        step = mech.act(st, opt, rng, p)
        hp += min(0, step.dmg.get("hp", 0))
        san += min(0, step.dmg.get("sanity", 0))
        if step.outcome != "continue":
            return step.outcome, hp, san
    return "timeout", hp, san


def rand_policy(mech, st, scene, rng):
    return rng.choice([o.id for o in scene.options if not o.item])


def smart(mech, st, scene, rng):
    mid = mech.id
    if mid == "quy_thu":
        return "dung_yen"
    if mid == "quy_anh":
        return next(o.id for o, l in zip(scene.options, st["spots"]) if l != 1)
    if mid == "quy_nhan":
        return "nham_mat" if st["gaze"] >= 2 else ("lui" if st["dist"] > 1 else "nham_mat")
    if mid == "quy_quan_tai":
        return "dong_nap"
    if mid == "quy_mon":
        return "im_lang" if st["knocks"] % 2 else "mo_cua"
    if mid == "quy_vuc":                      # biết trục: thăm dò rồi phá neo đúng hướng
        axis = [0, 2] if st["anchor"] % 2 == 0 else [1, 3]
        return f"pha_neo_{st['anchor']}" if st["probes"] else f"tham_do_{axis[0]}"
    raise KeyError(mid)


def summarize(label, runs):
    wins = sum(1 for r in runs if r[0] == "survive")
    dmg = statistics.mean(-(r[1] + r[2]) for r in runs if r[0] == "survive") if wins else 0
    return f"{label}: sống sót {100 * wins / len(runs):5.1f}%  (sát thương TB khi sống {dmg:4.1f})"


def economy(sessions=60):
    """Một 'phiên chơi' = chơi tới khi cạn tinh thần ở Khu Dân Cư, xử lý đối mặt bằng lựa chọn ngẫu nhiên (người chơi chưa có manh mối)."""
    from tests.helpers import make_game, mkplayer
    out = {"coins": [], "items": [], "explores": [], "deaths": 0, "encounters": 0, "survived": 0, "bound": 0}
    for s in range(sessions):
        g = make_game(500 + s)
        mkplayer(g, 1, loc="khu_dan_cu", level=3)
        start_coins = g.players.get(1)["coins"]
        n = 0
        while n < 200:
            p = g.players.get(1)
            if p["location_id"] != "khu_dan_cu" or p["sanity"] <= 12 or p["hp"] <= 12:
                break
            g.clock.advance(25)
            res = g.explore.explore(1, ("tham_do", "tim_do", "dieu_tra")[n % 3])
            n += 1
            if res["encounter"]:
                out["encounters"] += 1
                while g.enc.active(1):
                    v = g.enc.view(1)
                    if v["phase"] == "cleared":
                        out["survived"] += 1
                        g.rng.forced = None
                        if v["already_held"]:
                            g.enc.leave(1)
                        else:
                            out["bound"] += 1 if g.enc.bind(1)["success"] else 0
                        break
                    r = g.enc.act(1, g.rng.choice([o.id for o in v["scene"].options if not o.item]))
                    if r["status"] in ("death", "saved", "breakdown"):
                        out["deaths"] += r["status"] == "death"
                        break
        items = sum(r["qty"] for r in g.inv.list(1))
        out["coins"].append(g.players.get(1)["coins"] - start_coins)
        out["items"].append(items)
        out["explores"].append(n)
    m = statistics.mean
    print(f"\nKinh tế/phiên ({sessions} phiên, cấp 3 ở Khu Dân Cư, không manh mối, đến khi cạn tinh thần):")
    print(f"  khám phá TB {m(out['explores']):.1f} lượt  | tiền cổ ròng TB {m(out['coins']):+.0f}  | vật phẩm TB {m(out['items']):.1f}")
    print(f"  gặp quỷ {out['encounters']}, sống sót {out['survived']} ({100 * out['survived'] / max(1, out['encounters']):.0f}%), "
          f"chết {out['deaths']}, khống chế thành công {out['bound']}")


def main():
    rows = []
    for mid, mech in MECHANICS.items():
        rng = random.Random(1)
        blind = [play(mech, rng, rand_policy, set()) for _ in range(N)]
        informed = [play(mech, rng, smart, {0, 1, 2}) for _ in range(N)]
        rows.append((mid, summarize("mù", blind), summarize("biết", informed)))
    for mid, a, b in rows:
        print(f"{mid:13s} | {a} | {b}")
    economy()


if __name__ == "__main__":
    main()

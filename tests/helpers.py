import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.clock import Clock
from core.database import Database
from engine.game import Game


class FakeClock(Clock):
    def __init__(self, t=1_800_000_000):
        self.t = t

    def now(self):
        return self.t

    def advance(self, s):
        self.t += int(s)


class StubRng(random.Random):
    """RNG có thể ép random() để test nhánh may rủi."""
    forced = None

    def random(self):
        return super().random() if self.forced is None else self.forced


def make_game(seed=1):
    clock = FakeClock()
    db = Database(":memory:", clock).connect()
    db.migrate(ROOT / "migrations")
    return Game(db, clock, StubRng(seed))


def mkplayer(g, uid=1, origin="canh_sat", name="Tester", loc=None, level=None, sanity=None, coins=None):
    g.players.create(uid, name, origin)
    sets, vals = [], []
    for col, v in (("location_id", loc), ("level", level), ("sanity", sanity), ("coins", coins)):
        if v is not None:
            sets.append(f"{col}=?")
            vals.append(v)
    if sets:
        g.db.run(f"UPDATE players SET {','.join(sets)} WHERE user_id=?", (*vals, uid))
    return g.players.get(uid)

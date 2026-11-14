-- Giai đoạn 1: người chơi, túi đồ, lịch sử, thành tựu, bộ đếm
CREATE TABLE players (
    user_id       INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL,
    origin        TEXT    NOT NULL,
    created_at    INTEGER NOT NULL,
    level         INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
    exp           INTEGER NOT NULL DEFAULT 0 CHECK (exp >= 0),
    hp            INTEGER NOT NULL CHECK (hp >= 0),
    max_hp        INTEGER NOT NULL,
    sanity        INTEGER NOT NULL CHECK (sanity >= 0),
    max_sanity    INTEGER NOT NULL,
    corruption    INTEGER NOT NULL DEFAULT 0 CHECK (corruption BETWEEN 0 AND 100),
    reputation    INTEGER NOT NULL DEFAULT 0 CHECK (reputation >= 0),
    coins         INTEGER NOT NULL DEFAULT 0 CHECK (coins >= 0),
    location_id   TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'binh_thuong'
                  CHECK (status IN ('binh_thuong','nhiem_linh_di','mat_kiem_soat')),
    status_until  INTEGER NOT NULL DEFAULT 0,
    is_summoner   INTEGER NOT NULL DEFAULT 0,
    last_regen_at INTEGER NOT NULL
);

CREATE TABLE inventory (
    user_id INTEGER NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
    item_id TEXT    NOT NULL,
    qty     INTEGER NOT NULL CHECK (qty > 0),
    PRIMARY KEY (user_id, item_id)
);

CREATE TABLE player_history (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
    ts      INTEGER NOT NULL,
    kind    TEXT    NOT NULL,
    text    TEXT    NOT NULL
);
CREATE INDEX idx_history_user ON player_history(user_id, id DESC);

CREATE TABLE player_achievements (
    user_id INTEGER NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
    ach_id  TEXT    NOT NULL,
    ts      INTEGER NOT NULL,
    PRIMARY KEY (user_id, ach_id)
);

CREATE TABLE stats (
    user_id INTEGER NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
    key     TEXT    NOT NULL,
    value   INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, key)
);

CREATE TABLE cooldowns (
    user_id  INTEGER NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
    key      TEXT    NOT NULL,
    until_ts INTEGER NOT NULL,
    PRIMARY KEY (user_id, key)
);

CREATE TABLE buffs (
    user_id  INTEGER NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
    key      TEXT    NOT NULL,
    value    INTEGER NOT NULL,
    until_ts INTEGER NOT NULL,
    PRIMARY KEY (user_id, key)
);

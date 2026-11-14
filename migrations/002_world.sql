-- Giai đoạn 3: thế giới, lệ quỷ, manh mối, cuộc đối mặt
CREATE TABLE location_state (
    location_id  TEXT PRIMARY KEY,
    danger_mod   INTEGER NOT NULL DEFAULT 0 CHECK (danger_mod BETWEEN -3 AND 5),
    locked_until INTEGER NOT NULL DEFAULT 0,
    lock_reason  TEXT    NOT NULL DEFAULT '',
    explored     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE world_state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE ghost_instances (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ghost_id      TEXT    NOT NULL,
    state         TEXT    NOT NULL CHECK (state IN ('free','bound','sealed')),
    owner_id      INTEGER REFERENCES players(user_id) ON DELETE SET NULL,
    location_id   TEXT,
    resurrection  REAL    NOT NULL DEFAULT 0 CHECK (resurrection >= 0),
    uses          INTEGER NOT NULL DEFAULT 0,
    stable_uses   INTEGER NOT NULL DEFAULT 0,
    awakened      INTEGER NOT NULL DEFAULT 0,
    updated_at    INTEGER NOT NULL,
    created_at    INTEGER NOT NULL,
    CHECK ((state = 'free' AND owner_id IS NULL) OR (state <> 'free' AND owner_id IS NOT NULL))
);
CREATE INDEX idx_ghost_owner ON ghost_instances(owner_id, state);
CREATE INDEX idx_ghost_loc   ON ghost_instances(location_id, state);

CREATE TABLE player_clues (
    user_id   INTEGER NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
    ghost_id  TEXT    NOT NULL,
    clue_idx  INTEGER NOT NULL,
    found_at  INTEGER NOT NULL,
    PRIMARY KEY (user_id, ghost_id, clue_idx)
);

CREATE TABLE encounters (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL UNIQUE REFERENCES players(user_id) ON DELETE CASCADE,
    ghost_instance_id INTEGER NOT NULL REFERENCES ghost_instances(id) ON DELETE CASCADE,
    ghost_id          TEXT    NOT NULL,
    location_id       TEXT    NOT NULL,
    state_json        TEXT    NOT NULL,
    created_at        INTEGER NOT NULL
);

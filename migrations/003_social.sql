-- Giai đoạn 4-5: tổ chức, giao dịch, sự kiện, nhiệm vụ, cốt truyện nhiều kết cục
CREATE TABLE orgs (
    id         INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL UNIQUE,
    treasury   INTEGER NOT NULL DEFAULT 0 CHECK (treasury >= 0),
    created_at INTEGER NOT NULL
);
INSERT INTO orgs(id, name, treasury, created_at)
VALUES (1, 'Tổng Bộ Linh Dị', 500, CAST(strftime('%s','now') AS INTEGER));

CREATE TABLE org_members (
    org_id       INTEGER NOT NULL REFERENCES orgs(id),
    user_id      INTEGER NOT NULL UNIQUE REFERENCES players(user_id) ON DELETE CASCADE,
    rank         TEXT    NOT NULL CHECK (rank IN ('thanh_vien','doi_truong','phu_trach','tong_bo')),
    region       TEXT,
    contribution INTEGER NOT NULL DEFAULT 0,
    joined_at    INTEGER NOT NULL,
    PRIMARY KEY (org_id, user_id)
);

CREATE TABLE org_missions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id         INTEGER NOT NULL REFERENCES orgs(id),
    title          TEXT    NOT NULL,
    objective_json TEXT    NOT NULL,
    reward_json    TEXT    NOT NULL,
    escrow         INTEGER NOT NULL DEFAULT 0,
    issued_by      INTEGER NOT NULL REFERENCES players(user_id),
    assigned_to    INTEGER REFERENCES players(user_id),
    region         TEXT,
    status         TEXT    NOT NULL DEFAULT 'open'
                   CHECK (status IN ('open','taken','done','expired')),
    progress       INTEGER NOT NULL DEFAULT 0,
    created_at     INTEGER NOT NULL,
    deadline       INTEGER NOT NULL
);
CREATE INDEX idx_missions_status ON org_missions(status, deadline);

CREATE TABLE org_reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id      INTEGER NOT NULL REFERENCES orgs(id),
    author_id   INTEGER NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
    location_id TEXT    NOT NULL,
    event_id    INTEGER,
    text        TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
    reviewed_by INTEGER REFERENCES players(user_id),
    created_at  INTEGER NOT NULL
);

CREATE TABLE trades (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    from_user  INTEGER NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
    to_user    INTEGER NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
    give_json  TEXT    NOT NULL,
    want_json  TEXT    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'pending'
               CHECK (status IN ('pending','accepted','declined','cancelled','expired')),
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    CHECK (from_user <> to_user)
);
CREATE INDEX idx_trades_to ON trades(to_user, status);

CREATE TABLE world_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    def_id        TEXT    NOT NULL,
    kind          TEXT    NOT NULL CHECK (kind IN ('contrib','global','timed')),
    title         TEXT    NOT NULL,
    location_id   TEXT,
    ghost_instance_id INTEGER REFERENCES ghost_instances(id) ON DELETE SET NULL,
    state         TEXT    NOT NULL DEFAULT 'active' CHECK (state IN ('active','resolved','failed','expired')),
    progress      INTEGER NOT NULL DEFAULT 0,
    goal          INTEGER NOT NULL DEFAULT 0,
    started_at    INTEGER NOT NULL,
    ends_at       INTEGER NOT NULL
);
CREATE INDEX idx_events_state ON world_events(state, ends_at);

CREATE TABLE event_participants (
    event_id     INTEGER NOT NULL REFERENCES world_events(id) ON DELETE CASCADE,
    user_id      INTEGER NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
    contribution INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (event_id, user_id)
);

CREATE TABLE quests (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
    quest_id     TEXT    NOT NULL,
    status       TEXT    NOT NULL DEFAULT 'active' CHECK (status IN ('active','done')),
    progress     INTEGER NOT NULL DEFAULT 0,
    accepted_at  INTEGER NOT NULL,
    completed_at INTEGER,
    UNIQUE (user_id, quest_id)
);

CREATE TABLE story_states (
    user_id    INTEGER PRIMARY KEY REFERENCES players(user_id) ON DELETE CASCADE,
    story_id   TEXT    NOT NULL,
    node       TEXT    NOT NULL,
    started_at INTEGER NOT NULL
);

CREATE TABLE story_endings (
    user_id   INTEGER NOT NULL REFERENCES players(user_id) ON DELETE CASCADE,
    story_id  TEXT    NOT NULL,
    ending_id TEXT    NOT NULL,
    ts        INTEGER NOT NULL,
    PRIMARY KEY (user_id, story_id, ending_id)
);

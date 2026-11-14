-- Hồ sơ linh dị (灵异档案) của Tổng Bộ: kho giam giữ và tri thức dùng chung
CREATE TABLE org_archive (
    org_id        INTEGER NOT NULL REFERENCES orgs(id),
    ghost_id      TEXT    NOT NULL,
    held          INTEGER NOT NULL DEFAULT 0 CHECK (held >= 0),
    total_handed  INTEGER NOT NULL DEFAULT 0 CHECK (total_handed >= 0),
    first_by      INTEGER REFERENCES players(user_id) ON DELETE SET NULL,
    first_at      INTEGER NOT NULL,
    PRIMARY KEY (org_id, ghost_id)
);

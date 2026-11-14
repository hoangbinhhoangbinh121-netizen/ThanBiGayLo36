-- Giai đoạn 6: sổ đăng ký emoji ứng dụng đã tải lên Discord
CREATE TABLE emoji_registry (
    name        TEXT PRIMARY KEY,
    discord_id  INTEGER NOT NULL,
    uploaded_at INTEGER NOT NULL
);
CREATE INDEX idx_quests_user ON quests(user_id, status);
CREATE INDEX idx_members_org ON org_members(org_id, rank);

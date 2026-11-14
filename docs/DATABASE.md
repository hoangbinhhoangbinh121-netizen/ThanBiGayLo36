# Cơ sở dữ liệu

SQLite, 25 bảng, phiên bản schema 5. Khóa ngoại bật (`PRAGMA foreign_keys=ON`), ràng buộc CHECK ở mức DB (chỉ số không âm, trạng thái hợp lệ, quỷ tự do không có chủ...).

Quan hệ chính: `players` là gốc; hầu hết bảng tham chiếu `players(user_id)` với `ON DELETE CASCADE`. `ghost_instances` tham chiếu chủ sở hữu; `encounters`, `world_events`, `org_*`, `trades`, `quests`... nối vào cả hai.

## `buffs`
Cột: `user_id` (PK), `key` (PK), `value`, `until_ts`

Khóa ngoại: `user_id` → `players.user_id` (CASCADE)

## `cooldowns`
Cột: `user_id` (PK), `key` (PK), `until_ts`

Khóa ngoại: `user_id` → `players.user_id` (CASCADE)

## `emoji_registry`
Cột: `name` (PK), `discord_id`, `uploaded_at`

## `encounters`
Cột: `id` (PK), `user_id`, `ghost_instance_id`, `ghost_id`, `location_id`, `state_json`, `created_at`

Khóa ngoại: `ghost_instance_id` → `ghost_instances.id` (CASCADE), `user_id` → `players.user_id` (CASCADE)

## `event_participants`
Cột: `event_id` (PK), `user_id` (PK), `contribution`

Khóa ngoại: `user_id` → `players.user_id` (CASCADE), `event_id` → `world_events.id` (CASCADE)

## `ghost_instances`
Cột: `id` (PK), `ghost_id`, `state`, `owner_id`, `location_id`, `resurrection`, `uses`, `stable_uses`, `awakened`, `updated_at`, `created_at`

Khóa ngoại: `owner_id` → `players.user_id` (SET NULL)

## `inventory`
Cột: `user_id` (PK), `item_id` (PK), `qty`

Khóa ngoại: `user_id` → `players.user_id` (CASCADE)

## `location_state`
Cột: `location_id` (PK), `danger_mod`, `locked_until`, `lock_reason`, `explored`

## `org_archive`
Cột: `org_id` (PK), `ghost_id` (PK), `held`, `total_handed`, `first_by`, `first_at`

Khóa ngoại: `first_by` → `players.user_id` (SET NULL), `org_id` → `orgs.id` (NO ACTION)

## `org_members`
Cột: `org_id` (PK), `user_id` (PK), `rank`, `region`, `contribution`, `joined_at`

Khóa ngoại: `user_id` → `players.user_id` (CASCADE), `org_id` → `orgs.id` (NO ACTION)

## `org_missions`
Cột: `id` (PK), `org_id`, `title`, `objective_json`, `reward_json`, `escrow`, `issued_by`, `assigned_to`, `region`, `status`, `progress`, `created_at`, `deadline`

Khóa ngoại: `assigned_to` → `players.user_id` (NO ACTION), `issued_by` → `players.user_id` (NO ACTION), `org_id` → `orgs.id` (NO ACTION)

## `org_reports`
Cột: `id` (PK), `org_id`, `author_id`, `location_id`, `event_id`, `text`, `status`, `reviewed_by`, `created_at`

Khóa ngoại: `reviewed_by` → `players.user_id` (NO ACTION), `author_id` → `players.user_id` (CASCADE), `org_id` → `orgs.id` (NO ACTION)

## `orgs`
Cột: `id` (PK), `name`, `treasury`, `created_at`

## `player_achievements`
Cột: `user_id` (PK), `ach_id` (PK), `ts`

Khóa ngoại: `user_id` → `players.user_id` (CASCADE)

## `player_clues`
Cột: `user_id` (PK), `ghost_id` (PK), `clue_idx` (PK), `found_at`

Khóa ngoại: `user_id` → `players.user_id` (CASCADE)

## `player_history`
Cột: `id` (PK), `user_id`, `ts`, `kind`, `text`

Khóa ngoại: `user_id` → `players.user_id` (CASCADE)

## `players`
Cột: `user_id` (PK), `name`, `origin`, `created_at`, `level`, `exp`, `hp`, `max_hp`, `sanity`, `max_sanity`, `corruption`, `reputation`, `coins`, `location_id`, `status`, `status_until`, `is_summoner`, `last_regen_at`

## `quests`
Cột: `id` (PK), `user_id`, `quest_id`, `status`, `progress`, `accepted_at`, `completed_at`

Khóa ngoại: `user_id` → `players.user_id` (CASCADE)

## `schema_migrations`
Cột: `version` (PK), `name`, `applied_at`

## `stats`
Cột: `user_id` (PK), `key` (PK), `value`

Khóa ngoại: `user_id` → `players.user_id` (CASCADE)

## `story_endings`
Cột: `user_id` (PK), `story_id` (PK), `ending_id` (PK), `ts`

Khóa ngoại: `user_id` → `players.user_id` (CASCADE)

## `story_states`
Cột: `user_id` (PK), `story_id`, `node`, `started_at`

Khóa ngoại: `user_id` → `players.user_id` (CASCADE)

## `trades`
Cột: `id` (PK), `from_user`, `to_user`, `give_json`, `want_json`, `status`, `created_at`, `expires_at`

Khóa ngoại: `to_user` → `players.user_id` (CASCADE), `from_user` → `players.user_id` (CASCADE)

## `world_events`
Cột: `id` (PK), `def_id`, `kind`, `title`, `location_id`, `ghost_instance_id`, `state`, `progress`, `goal`, `started_at`, `ends_at`

Khóa ngoại: `ghost_instance_id` → `ghost_instances.id` (SET NULL)

## `world_state`
Cột: `key` (PK), `value`

CREATE SCHEMA IF NOT EXISTS app_chat;

CREATE TABLE IF NOT EXISTS app_chat.chat_history (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES app_auth.users(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_history_user_created
ON app_chat.chat_history(user_id, created_at DESC);

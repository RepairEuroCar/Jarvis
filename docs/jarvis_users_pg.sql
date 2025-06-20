-- PostgreSQL schema for Jarvis users with improvements
-- Run this script to set up the database tables used by the assistant

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Main user table
CREATE TABLE IF NOT EXISTS jarvis_users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(75) UNIQUE NOT NULL CHECK (username ~ '^[a-z0-9_]{3,}$'),
    voiceprint_hash TEXT,
    biometric_signature BYTEA,
    security_level INT NOT NULL DEFAULT 1 CHECK (security_level BETWEEN 1 AND 5),
    jarvis_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    skill_matrix JSONB NOT NULL DEFAULT '{}'::jsonb,
    work_environment JSONB NOT NULL DEFAULT '{}'::jsonb,
    learning_adaptation JSONB NOT NULL DEFAULT '{}'::jsonb,
    connected_services JSONB NOT NULL DEFAULT '{}'::jsonb,
    access_control JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    config_version INT NOT NULL DEFAULT 1,
    last_failed_login TIMESTAMPTZ,
    failed_login_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_interaction TIMESTAMPTZ,
    last_training_session TIMESTAMPTZ,
    last_security_check TIMESTAMPTZ,
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('simple', coalesce(username, ''))
    ) STORED
);

-- Authentication tokens stored separately
CREATE TABLE IF NOT EXISTS jarvis_auth_tokens (
    token_id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES jarvis_users(user_id) ON DELETE CASCADE,
    auth_token TEXT NOT NULL,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Audit log for important changes
CREATE TABLE IF NOT EXISTS jarvis_user_audit (
    audit_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES jarvis_users(user_id) ON DELETE CASCADE,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,
    old_data JSONB,
    new_data JSONB
);

-- Threat detection history split into a separate table
CREATE TABLE IF NOT EXISTS jarvis_threat_history (
    entry_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES jarvis_users(user_id) ON DELETE CASCADE,
    event_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    result TEXT NOT NULL
);

-- Example trigger: log security checks
CREATE OR REPLACE FUNCTION log_security_scan()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.last_security_check IS DISTINCT FROM OLD.last_security_check THEN
        INSERT INTO jarvis_threat_history(user_id, event_type, result)
        VALUES (NEW.user_id, 'security_scan',
                CASE WHEN NEW.security_level < 3 THEN 'warning' ELSE 'clean' END);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_security_scan
AFTER UPDATE ON jarvis_users
FOR EACH ROW
EXECUTE FUNCTION log_security_scan();

-- Materialized view of active users
CREATE MATERIALIZED VIEW IF NOT EXISTS jarvis_active_users AS
SELECT
    u.user_id,
    u.username,
    u.jarvis_config->'personality'->>'mode' AS personality_mode,
    (u.skill_matrix->'python'->>'oop')::numeric AS oop_skill,
    u.last_interaction
FROM jarvis_users u
WHERE u.last_interaction > (CURRENT_TIMESTAMP - INTERVAL '7 days')
WITH DATA;

-- Indexes for JSONB fields and search
CREATE INDEX IF NOT EXISTS idx_users_search ON jarvis_users USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_users_skill_python ON jarvis_users USING GIN ((skill_matrix->'python'));
CREATE INDEX IF NOT EXISTS idx_users_work_env ON jarvis_users USING GIN ((work_environment->'ide_state'));

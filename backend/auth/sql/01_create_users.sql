-- ============================================================
-- Tennis EXPLORE - Auth Users Schema
-- PostgreSQL 16
-- Purpose:
-- Stores application users for login. Seeded with default
-- accounts so no separate python seeder is required on server.
-- ============================================================

CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.users (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'coach',
    profile_pic TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON auth.users(email);

-- Keep updated_at in sync on UPDATE
CREATE OR REPLACE FUNCTION auth.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON auth.users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON auth.users
    FOR EACH ROW EXECUTE FUNCTION auth.set_updated_at();

-- ------------------------------------------------------------
-- Seed default users (idempotent)
-- Default admin: admin@tennisexplore.au / admin123 (role: admin)
-- Hashes generated with bcrypt (passlib, cost 12)
-- ------------------------------------------------------------
INSERT INTO auth.users (name, email, password_hash, role)
VALUES (
    'Admin',
    'admin@tennisexplore.au',
    '$2b$12$DFzyShjGFLBo/7bXfwA8X.FqGJhImcAyDsEBaOQEdQ9yxmU/4H2p2',
    'admin'
)
ON CONFLICT (email) DO NOTHING;

-- Additional coach user for testing (password: coach123)
-- Hash for 'coach123' generated with bcrypt cost 12
INSERT INTO auth.users (name, email, password_hash, role)
VALUES (
    'Coach',
    'coach@tennisexplore.au',
    '$2b$12$Ly.r6vcwbHZ2azaw6/30CORute/Gm.XYVgGyDJJZQ7hPJ8HK39wrC',
    'coach'
)
ON CONFLICT (email) DO NOTHING;

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
    role VARCHAR(50) NOT NULL DEFAULT 'Analyst',
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
-- Password for analyst@tennisexplore.au is 'ace123'
-- Hash generated with bcrypt (passlib, cost 12) - verified to
-- work with backend passlib/Bcrypt 4.0.1
-- ------------------------------------------------------------
INSERT INTO auth.users (name, email, password_hash, role)
VALUES (
    'Alex Rivera',
    'analyst@tennisexplore.au',
    '$2b$12$ZJC0tcGnqExKItxxKRV46uoxsqa8L75Zg87VgUUXKQDLs8lVv9AsK',
    'Lead Analyst'
)
ON CONFLICT (email) DO NOTHING;

-- Additional default user for admin testing (password: admin123)
-- Hash for 'admin123'
INSERT INTO auth.users (name, email, password_hash, role)
VALUES (
    'Admin',
    'admin@tennisexplore.au',
    '$2b$12$DFzyShjGFLBo/7bXfwA8X.FqGJhImcAyDsEBaOQEdQ9yxmU/4H2p2',
    'Admin'
)
ON CONFLICT (email) DO NOTHING;

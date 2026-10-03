CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS staging.raw_rankings (
    raw_record_id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_format TEXT NOT NULL,
    snapshot_date DATE,
    row_number INTEGER,
    raw_data JSONB NOT NULL,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_raw_rankings_source_file_row
ON staging.raw_rankings (source, file_name, row_number);

CREATE TABLE IF NOT EXISTS core.players (
    player_id BIGSERIAL PRIMARY KEY,
    full_name TEXT,
    first_name TEXT,
    last_name TEXT,
    gender TEXT,
    country TEXT,
    birth_year INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS core.player_identifiers (
    identifier_id BIGSERIAL PRIMARY KEY,
    player_id BIGINT REFERENCES core.players(player_id),
    source TEXT NOT NULL,
    source_player_id TEXT NOT NULL,
    UNIQUE (source, source_player_id)
);

CREATE TABLE IF NOT EXISTS core.ranking_snapshots (
    ranking_id BIGSERIAL PRIMARY KEY,
    player_id BIGINT REFERENCES core.players(player_id),
    source TEXT NOT NULL,
    ranking_type TEXT,
    rank INTEGER,
    points NUMERIC,
    rating NUMERIC,
    snapshot_date DATE,
    raw_record_id BIGINT REFERENCES staging.raw_rankings(raw_record_id)
);
CREATE INDEX IF NOT EXISTS idx_ranking_snapshots_raw_record_id
ON core.ranking_snapshots (raw_record_id);

-- ============================================================
-- Tennis Australia Athlete Reference
-- ============================================================
-- Curated athlete identity information supplied directly by
-- Tennis Australia.
--
-- This reference complements the broader ATP/WTA/ITF/UTR
-- ranking datasets and provides trusted cross-organisation
-- identifiers for athletes tracked by Tennis Australia.
-- ============================================================

CREATE TABLE IF NOT EXISTS core.ta_athletes (
    ta_athlete_id BIGSERIAL PRIMARY KEY,
    athlete_name TEXT NOT NULL,
    dob DATE,
    state TEXT,
    program TEXT,
    pro_id TEXT,
    itf_id TEXT,
    utr_ids TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Tennis EXPLORE
-- Ranking History Processing
--
-- Purpose:
-- Build ranking and rating history for mapped players from
-- ATP, WTA, ITF and UTR supplied data.
--
-- Player identity is handled separately in:
--   03_player_identity.sql
--
-- This file uses the existing player mappings and does not
-- create or change player identities.
-- ============================================================


-- ============================================================
-- 1. ATP Ranking Data Exploration
-- ============================================================
-- ATP ranking records may contain singles and doubles rankings.
-- Before loading ranking history, inspect the supplied fields
-- and confirm how ranking dates and missing values are stored.
-- ============================================================

SELECT
    snapshot_date,
    raw_data->>'tourid' AS tour_id,
    raw_data->>'firstname' AS first_name,
    raw_data->>'lastname' AS last_name,
    raw_data->>'sglrank' AS singles_rank,
    raw_data->>'dblrank' AS doubles_rank,
    raw_data->>'rankdate' AS rank_date
FROM staging.raw_rankings
WHERE source = 'ATP'
ORDER BY snapshot_date, raw_record_id
LIMIT 10;
-- ============================================================
-- 2. Validate ATP Ranking Fields
-- ============================================================
-- Confirm ranking-date consistency and determine how many
-- supplied ATP records contain singles and/or doubles rankings.
-- ============================================================

SELECT
    COUNT(*) AS total_atp_records,

    COUNT(*) FILTER (
        WHERE NULLIF(TRIM(raw_data->>'sglrank'), '') IS NOT NULL
    ) AS records_with_singles_rank,

    COUNT(*) FILTER (
        WHERE NULLIF(TRIM(raw_data->>'dblrank'), '') IS NOT NULL
    ) AS records_with_doubles_rank,

    COUNT(*) FILTER (
        WHERE NULLIF(TRIM(raw_data->>'sglrank'), '') IS NULL
          AND NULLIF(TRIM(raw_data->>'dblrank'), '') IS NULL
    ) AS records_with_no_rank,

    COUNT(*) FILTER (
        WHERE NULLIF(TRIM(raw_data->>'rankdate'), '') IS NOT NULL
          AND (raw_data->>'rankdate')::date <> snapshot_date
    ) AS rankdate_snapshot_mismatch

FROM staging.raw_rankings
WHERE source = 'ATP';
-- ============================================================
-- 3. Validate ATP Player Mapping Before Ranking Load
-- ============================================================
-- Confirm that ATP ranking records can be linked to the
-- master player model through their ATP tour ID.
--
-- No ranking data is inserted in this section.
-- ============================================================

SELECT
    COUNT(*) AS total_atp_records,

    COUNT(*) FILTER (
        WHERE pi.player_id IS NOT NULL
    ) AS mapped_records,

    COUNT(*) FILTER (
        WHERE pi.player_id IS NULL
    ) AS unmapped_records,

    COUNT(DISTINCT raw.raw_data->>'tourid') AS distinct_atp_ids,

    COUNT(DISTINCT raw.raw_data->>'tourid') FILTER (
        WHERE pi.player_id IS NULL
    ) AS unmapped_atp_ids

FROM staging.raw_rankings raw

LEFT JOIN core.player_identifiers pi
    ON pi.source = 'ATP'
   AND pi.source_player_id = raw.raw_data->>'tourid'

WHERE raw.source = 'ATP';
-- ============================================================
-- 4. Load ATP Singles Ranking History
-- ============================================================
-- Create one ranking-history row for every supplied ATP record
-- containing a singles ranking.
--
-- ATP tour IDs are linked to the existing master player model
-- through core.player_identifiers.
-- ============================================================
WITH unique_atp AS (
    SELECT DISTINCT ON (file_name, row_number)
        raw_record_id,
        raw_data,
        snapshot_date,
        file_name,
        row_number
    FROM staging.raw_rankings
    WHERE source = 'ATP'
    ORDER BY file_name, row_number, raw_record_id
)
INSERT INTO core.ranking_snapshots (
    player_id,
    source,
    ranking_type,
    rank,
    points,
    rating,
    snapshot_date,
    raw_record_id
)
SELECT
    pi.player_id,
    'ATP',
    'singles',
    (raw.raw_data->>'sglrank')::INTEGER,
    NULL,
    NULL,
    (raw.raw_data->>'rankdate')::DATE,
    raw.raw_record_id
FROM unique_atp raw
JOIN core.player_identifiers pi
    ON pi.source = 'ATP'
   AND pi.source_player_id = raw.raw_data->>'tourid'
WHERE NULLIF(TRIM(raw.raw_data->>'sglrank'), '') IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM core.ranking_snapshots rs
      WHERE rs.raw_record_id = raw.raw_record_id
        AND rs.source = 'ATP'
        AND rs.ranking_type = 'singles'
  );
-- ============================================================
-- 5. Load ATP Doubles Ranking History
-- ============================================================
-- Create one ranking-history row for every supplied ATP record
-- containing a doubles ranking.
-- ============================================================
WITH unique_atp AS (
    SELECT DISTINCT ON (file_name, row_number)
        raw_record_id,
        raw_data,
        snapshot_date,
        file_name,
        row_number
    FROM staging.raw_rankings
    WHERE source = 'ATP'
    ORDER BY file_name, row_number, raw_record_id
)
INSERT INTO core.ranking_snapshots (
    player_id,
    source,
    ranking_type,
    rank,
    points,
    rating,
    snapshot_date,
    raw_record_id
)
SELECT
    pi.player_id,
    'ATP',
    'doubles',
    (raw.raw_data->>'dblrank')::INTEGER,
    NULL,
    NULL,
    (raw.raw_data->>'rankdate')::DATE,
    raw.raw_record_id
FROM unique_atp raw
JOIN core.player_identifiers pi
    ON pi.source = 'ATP'
   AND pi.source_player_id = raw.raw_data->>'tourid'
WHERE NULLIF(TRIM(raw.raw_data->>'dblrank'), '') IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM core.ranking_snapshots rs
      WHERE rs.raw_record_id = raw.raw_record_id
        AND rs.source = 'ATP'
        AND rs.ranking_type = 'doubles'
  );
-- ============================================================
-- 7. Load WTA Singles Ranking History
-- ============================================================
-- Create one ranking-history row for every supplied WTA record
-- containing a singles ranking.
-- ============================================================
WITH unique_wta AS (
    SELECT DISTINCT ON (file_name, row_number)
        raw_record_id,
        raw_data,
        snapshot_date,
        file_name,
        row_number
    FROM staging.raw_rankings
    WHERE source = 'WTA'
    ORDER BY file_name, row_number, raw_record_id
)
INSERT INTO core.ranking_snapshots (
    player_id,
    source,
    ranking_type,
    rank,
    points,
    rating,
    snapshot_date,
    raw_record_id
)
SELECT
    pi.player_id,
    'WTA',
    'singles',
    (raw.raw_data->>'sglrank')::INTEGER,
    NULL,
    NULL,
    (raw.raw_data->>'rankdate')::DATE,
    raw.raw_record_id
FROM unique_wta raw
JOIN core.player_identifiers pi
    ON pi.source = 'WTA'
   AND pi.source_player_id = raw.raw_data->>'tourid'
WHERE NULLIF(TRIM(raw.raw_data->>'sglrank'), '') IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM core.ranking_snapshots rs
      WHERE rs.raw_record_id = raw.raw_record_id
        AND rs.source = 'WTA'
        AND rs.ranking_type = 'singles'
  );
-- ============================================================
-- 8. Load WTA Doubles Ranking History
-- ============================================================
-- Create one ranking-history row for every supplied WTA record
-- containing a doubles ranking.
-- ============================================================
WITH unique_wta AS (
    SELECT DISTINCT ON (file_name, row_number)
        raw_record_id,
        raw_data,
        snapshot_date,
        file_name,
        row_number
    FROM staging.raw_rankings
    WHERE source = 'WTA'
    ORDER BY file_name, row_number, raw_record_id
)
INSERT INTO core.ranking_snapshots (
    player_id,
    source,
    ranking_type,
    rank,
    points,
    rating,
    snapshot_date,
    raw_record_id
)
SELECT
    pi.player_id,
    'WTA',
    'doubles',
    (raw.raw_data->>'dblrank')::INTEGER,
    NULL,
    NULL,
    (raw.raw_data->>'rankdate')::DATE,
    raw.raw_record_id
FROM unique_wta raw
JOIN core.player_identifiers pi
    ON pi.source = 'WTA'
   AND pi.source_player_id = raw.raw_data->>'tourid'
WHERE NULLIF(TRIM(raw.raw_data->>'dblrank'), '') IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM core.ranking_snapshots rs
      WHERE rs.raw_record_id = raw.raw_record_id
        AND rs.source = 'WTA'
        AND rs.ranking_type = 'doubles'
  );
-- ============================================================
-- 9. ITF RANKING HISTORY
-- ============================================================
-- ITF raw data contains a duplicated ingestion.
-- Keep only the earliest raw_record_id for each
-- (file_name, row_number) combination.
--
-- ITF supplied data contains usable rank and points values.
-- No usable doubles ranking values were found.

WITH unique_itf AS (
    SELECT DISTINCT ON (file_name, row_number)
        raw_record_id,
        snapshot_date,
        raw_data
    FROM staging.raw_rankings
    WHERE source = 'ITF'
    ORDER BY file_name, row_number, raw_record_id
)
INSERT INTO core.ranking_snapshots (
    player_id,
    source,
    ranking_type,
    rank,
    points,
    rating,
    snapshot_date,
    raw_record_id
)
SELECT
    pi.player_id,
    'ITF',
    'singles',
    NULLIF(u.raw_data->>'rank', '')::integer,
    NULLIF(u.raw_data->>'points', '')::numeric,
    NULL,
    u.snapshot_date,
    u.raw_record_id
FROM unique_itf u
JOIN core.player_identifiers pi
    ON pi.source = 'ITF'
   AND pi.source_player_id = u.raw_data->>'playerId'
WHERE NULLIF(u.raw_data->>'rank', '') IS NOT NULL
  AND NOT EXISTS (
      SELECT 1
      FROM core.ranking_snapshots rs
      WHERE rs.raw_record_id = u.raw_record_id
        AND rs.source = 'ITF'
        AND rs.ranking_type = 'singles'
  );
-- ============================================================
-- 10. UTR RATING HISTORY
-- ============================================================
-- UTR raw data contains a duplicated ingestion.
-- Keep only the earliest raw_record_id for each
-- (file_name, row_number) combination.
--
-- UTR provides ratings rather than ranking positions.
-- Unresolved UTR player identifiers are intentionally excluded
-- because they do not have a confirmed master-player mapping.


-- ------------------------------------------------------------
-- 10A. UTR SINGLES RATING HISTORY
-- ------------------------------------------------------------

WITH unique_utr AS (
    SELECT DISTINCT ON (file_name, row_number)
        raw_record_id,
        snapshot_date,
        raw_data,
        COALESCE(
            NULLIF(raw_data->>'playerid', ''),
            NULLIF(raw_data->>'utr_id', '')
        ) AS source_player_id
    FROM staging.raw_rankings
    WHERE source = 'UTR'
    ORDER BY file_name, row_number, raw_record_id
)
INSERT INTO core.ranking_snapshots (
    player_id,
    source,
    ranking_type,
    rank,
    points,
    rating,
    snapshot_date,
    raw_record_id
)
SELECT
    pi.player_id,
    'UTR',
    'singles',
    NULL,
    NULL,
    NULLIF(u.raw_data->>'singles_utr', '')::numeric,
    u.snapshot_date,
    u.raw_record_id
FROM unique_utr u
JOIN core.player_identifiers pi
    ON pi.source = 'UTR'
   AND pi.source_player_id = u.source_player_id
WHERE NULLIF(u.raw_data->>'singles_utr', '') IS NOT NULL
  AND UPPER(u.raw_data->>'singles_utr') <> 'NA'
  AND NOT EXISTS (
      SELECT 1
      FROM core.ranking_snapshots rs
      WHERE rs.raw_record_id = u.raw_record_id
        AND rs.source = 'UTR'
        AND rs.ranking_type = 'singles'
  );


-- ------------------------------------------------------------
-- 10B. UTR DOUBLES RATING HISTORY
-- ------------------------------------------------------------

WITH unique_utr AS (
    SELECT DISTINCT ON (file_name, row_number)
        raw_record_id,
        snapshot_date,
        raw_data,
        COALESCE(
            NULLIF(raw_data->>'playerid', ''),
            NULLIF(raw_data->>'utr_id', '')
        ) AS source_player_id
    FROM staging.raw_rankings
    WHERE source = 'UTR'
    ORDER BY file_name, row_number, raw_record_id
)
INSERT INTO core.ranking_snapshots (
    player_id,
    source,
    ranking_type,
    rank,
    points,
    rating,
    snapshot_date,
    raw_record_id
)
SELECT
    pi.player_id,
    'UTR',
    'doubles',
    NULL,
    NULL,
    NULLIF(u.raw_data->>'doubles_utr', '')::numeric,
    u.snapshot_date,
    u.raw_record_id
FROM unique_utr u
JOIN core.player_identifiers pi
    ON pi.source = 'UTR'
   AND pi.source_player_id = u.source_player_id
WHERE NULLIF(u.raw_data->>'doubles_utr', '') IS NOT NULL
  AND UPPER(u.raw_data->>'doubles_utr') <> 'NA'
  AND NOT EXISTS (
      SELECT 1
      FROM core.ranking_snapshots rs
      WHERE rs.raw_record_id = u.raw_record_id
        AND rs.source = 'UTR'
        AND rs.ranking_type = 'doubles'
  );

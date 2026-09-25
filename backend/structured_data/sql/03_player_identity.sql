-- ============================================================
-- Tennis EXPLORE
-- Player Identity Processing
--
-- Purpose:
-- Build reliable master player records from ATP, WTA, ITF and
-- UTR data using organisation IDs first, then carefully selected
-- supporting evidence.
--
-- Important:
-- Run this only after:
--   1. 01_create_schema.sql
--   2. raw data loading
--   3. 02_player_source_view.sql
--
-- Do NOT run this against the current live database while this
-- script is still being reconstructed and validated.
-- ============================================================
-- ============================================================
-- 1. Build ITF Master Player Map
-- ============================================================
-- Each distinct ITF source player ID becomes one internal
-- Tennis EXPLORE master player.
--
-- ITF source IDs are treated as direct organisation identity
-- evidence and are stronger than matching by name or country.
-- ============================================================

DROP TABLE IF EXISTS staging.itf_player_map;

CREATE TABLE staging.itf_player_map AS
SELECT DISTINCT ON (source_player_id)
    source_player_id AS itf_id,
    full_name,
    first_name,
    last_name,
    country,
    birth_date,
    NULL::bigint AS player_id
FROM staging.player_source_records
WHERE source = 'ITF'
  AND source_player_id IS NOT NULL
ORDER BY
    source_player_id,
    snapshot_date DESC NULLS LAST,
    raw_record_id DESC;


-- Assign one internal player_id per ITF source ID.
UPDATE staging.itf_player_map
SET player_id = nextval('core.players_player_id_seq')
WHERE player_id IS NULL;


-- Create the master player records.
INSERT INTO core.players (
    player_id,
    full_name,
    first_name,
    last_name,
    country,
    birth_year
)
SELECT
    player_id,
    full_name,
    first_name,
    last_name,
    country,
    EXTRACT(YEAR FROM birth_date)::integer
FROM staging.itf_player_map
ON CONFLICT (player_id) DO NOTHING;


-- Store the ITF organisation identifiers.
INSERT INTO core.player_identifiers (
    player_id,
    source,
    source_player_id
)
SELECT
    player_id,
    'ITF',
    itf_id
FROM staging.itf_player_map
ON CONFLICT (source, source_player_id) DO NOTHING;


-- Validation for the current supplied dataset.
-- Expected: 9,887 unique ITF players.
SELECT
    COUNT(*) AS total_itf_players,
    COUNT(DISTINCT itf_id) AS unique_itf_ids,
    COUNT(DISTINCT player_id) AS unique_player_ids
FROM staging.itf_player_map;
-- ============================================================
-- 2. Build ATP/WTA Player Lookup
-- ============================================================
-- ATP and WTA players appear in multiple ranking snapshots.
-- The organisation-specific source_player_id is treated as the
-- identity key.
--
-- Name and country are used only as representative metadata.
-- ============================================================

DROP TABLE IF EXISTS staging.atp_wta_player_lookup;

CREATE TABLE staging.atp_wta_player_lookup AS
SELECT DISTINCT ON (source, source_player_id)
    source,
    source_player_id,
    full_name,
    country
FROM staging.player_source_records
WHERE source IN ('ATP', 'WTA')
  AND source_player_id IS NOT NULL
ORDER BY
    source,
    source_player_id,
    snapshot_date DESC,
    raw_record_id DESC;


-- Validation for the current supplied dataset.
-- Expected:
--   ATP: 3,282 unique players
--   WTA: 2,110 unique players
SELECT
    source,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT source_player_id) AS unique_player_ids,
    COUNT(*) FILTER (
        WHERE full_name IS NULL OR TRIM(full_name) = ''
    ) AS missing_name,
    COUNT(*) FILTER (
        WHERE country IS NULL OR TRIM(country) = ''
    ) AS missing_country
FROM staging.atp_wta_player_lookup
GROUP BY source
ORDER BY source;
-- ============================================================
-- 3. Build Direct UTR -> ITF Match Evidence
-- ============================================================
-- Some UTR records contain an explicit ITF organisation ID.
-- These direct organisation-ID cross-references are stronger
-- identity evidence than matching by name or country.
--
-- Only ITF IDs that actually exist in the supplied ITF data
-- can be linked automatically.
-- ============================================================

DROP TABLE IF EXISTS staging.utr_itf_matches;

CREATE TABLE staging.utr_itf_matches AS
SELECT DISTINCT
    u.source_player_id AS utr_id,
    u.full_name AS utr_name,
    u.country AS utr_country,
    u.itf_id,
    i.full_name AS itf_name,
    i.country AS itf_country,
    i.itf_id AS itf_player_id
FROM staging.player_source_records u
JOIN staging.itf_player_map i
    ON i.itf_id = u.itf_id
WHERE u.source = 'UTR'
  AND u.source_player_id IS NOT NULL
  AND u.itf_id IS NOT NULL;


-- Validation.
-- Counts are checked during the fresh rebuild.
--
-- Historical note:
-- An earlier pass found 534 rows / 462 UTR IDs, but that was
-- before canonical UTR IDs were corrected to support both
-- playerid and utr_id. Do not use those earlier counts as the
-- final expected result.

SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT utr_id) AS unique_utr_ids,
    COUNT(DISTINCT itf_id) AS unique_itf_ids
FROM staging.utr_itf_matches;


-- Safety check.
-- Expected: zero rows.
-- A single UTR ID must not point to multiple ITF IDs.
SELECT
    utr_id,
    COUNT(DISTINCT itf_id) AS distinct_itf_ids
FROM staging.utr_itf_matches
GROUP BY utr_id
HAVING COUNT(DISTINCT itf_id) > 1
ORDER BY distinct_itf_ids DESC;
-- ============================================================
-- 4. Link UTR IDs to Existing ITF Master Players
-- ============================================================
-- Use the direct UTR -> ITF organisation-ID evidence created
-- in the previous section.
--
-- The ITF master player already exists, so we only add the UTR
-- identifier to that same internal player_id.
-- ============================================================

INSERT INTO core.player_identifiers (
    player_id,
    source,
    source_player_id
)
SELECT DISTINCT
    i.player_id,
    'UTR',
    m.utr_id
FROM staging.utr_itf_matches m
JOIN staging.itf_player_map i
    ON i.itf_id = m.itf_id
WHERE m.utr_id IS NOT NULL
  AND i.player_id IS NOT NULL
ON CONFLICT (source, source_player_id) DO NOTHING;


-- Validation.
SELECT
    COUNT(DISTINCT pi.source_player_id) AS linked_utr_ids,
    COUNT(DISTINCT pi.player_id) AS linked_itf_master_players
FROM core.player_identifiers pi
WHERE pi.source = 'UTR'
  AND EXISTS (
      SELECT 1
      FROM staging.utr_itf_matches m
      WHERE m.utr_id = pi.source_player_id
  );
-- ============================================================
-- 5. Link ATP/WTA IDs to Existing ITF Masters via UTR Evidence
-- ============================================================
-- Some UTR records explicitly contain both:
--   1. an ITF organisation ID, and
--   2. an ATP/WTA organisation ID.
--
-- When the referenced ITF player already has a master player,
-- the ATP/WTA identifier can be attached to that same master.
--
-- This is strong cross-organisation identity evidence because
-- the relationship comes directly from supplied source IDs,
-- rather than from name or country matching.
-- ============================================================

INSERT INTO core.player_identifiers (
    player_id,
    source,
    source_player_id
)
SELECT DISTINCT
    i.player_id,
    a.source,
    a.source_player_id
FROM staging.player_source_records u
JOIN staging.itf_player_map i
    ON i.itf_id = u.itf_id
JOIN staging.atp_wta_player_lookup a
    ON (
        (a.source = 'ATP'
         AND 'ATP' || UPPER(TRIM(u.atp_wta_id))
             = UPPER(a.source_player_id))
        OR
        (a.source = 'WTA'
         AND 'WTA' || UPPER(TRIM(u.atp_wta_id))
             = UPPER(a.source_player_id))
    )
WHERE u.source = 'UTR'
  AND u.source_player_id IS NOT NULL
  AND u.itf_id IS NOT NULL
  AND u.atp_wta_id IS NOT NULL
ON CONFLICT (source, source_player_id) DO NOTHING;


-- Validation.
-- This stage should include relationships such as:
--   ATPA0M2 -> ITF 800564683
--   ATPB0V0 -> ITF 800590346
SELECT
    source,
    COUNT(*) AS identifiers_on_itf_masters
FROM core.player_identifiers pi
WHERE pi.source IN ('ATP', 'WTA')
  AND EXISTS (
      SELECT 1
      FROM core.player_identifiers itf
      WHERE itf.player_id = pi.player_id
        AND itf.source = 'ITF'
  )
GROUP BY source
ORDER BY source;
-- ============================================================
-- 6. Build Canonical UTR Player Lookup
-- ============================================================
-- UTR players appear across repeated ranking snapshots.
-- staging.player_source_records has already normalised the two
-- possible UTR identifier fields: playerid and utr_id.
--
-- This table creates one lookup row per canonical UTR source ID.
-- It is used later after stronger cross-organisation matching
-- has been attempted.
-- ============================================================

DROP TABLE IF EXISTS staging.utr_player_lookup_v2;

CREATE TABLE staging.utr_player_lookup_v2 AS
SELECT
    source_player_id,
    MAX(NULLIF(TRIM(full_name), '')) AS full_name,
    MAX(NULLIF(TRIM(country), '')) AS country,
    MAX(birth_date) AS birth_date
FROM staging.player_source_records
WHERE source = 'UTR'
  AND source_player_id IS NOT NULL
GROUP BY source_player_id;


-- Validation for the current supplied dataset.
-- Expected: 111,143 canonical UTR source IDs.
SELECT
    COUNT(*) AS total_canonical_utr_ids,
    COUNT(DISTINCT source_player_id) AS unique_canonical_utr_ids
FROM staging.utr_player_lookup_v2;
-- 7. Build Remaining UTR -> ATP/WTA Tour Candidates
-- ============================================================
-- This stage handles UTR records containing explicit ATP/WTA
-- cross-references where the referenced tour player still has
-- no existing master-player mapping.
--
-- Multiple UTR IDs may point to one ATP/WTA player.
--
-- Current dataset validation:
--   ATP: 1,740 UTR links -> 1,641 tour players
--   WTA: 1,130 UTR links -> 1,107 tour players
--   Total: 2,870 UTR links -> 2,748 tour players
--   0 UTR IDs map to multiple master players
-- ============================================================

DROP TABLE IF EXISTS staging.utr_tour_candidates;

CREATE TABLE staging.utr_tour_candidates AS
SELECT DISTINCT
    u.source_player_id AS utr_id,
    a.source,
    a.source_player_id AS tour_player_id,
    a.full_name,
    a.country,
    NULL::bigint AS player_id
FROM staging.player_source_records u
JOIN staging.atp_wta_player_lookup a
    ON u.source = 'UTR'
   AND u.atp_wta_id IS NOT NULL
   AND (
        (a.source = 'ATP'
         AND 'ATP' || UPPER(TRIM(u.atp_wta_id))
             = UPPER(a.source_player_id))
        OR
        (a.source = 'WTA'
         AND 'WTA' || UPPER(TRIM(u.atp_wta_id))
             = UPPER(a.source_player_id))
   )
LEFT JOIN core.player_identifiers pi
    ON pi.source = a.source
   AND pi.source_player_id = a.source_player_id
WHERE pi.identifier_id IS NULL;


-- One internal master-player ID per ATP/WTA tour player.
WITH assigned AS (
    SELECT
        source,
        tour_player_id,
        nextval('core.players_player_id_seq') AS new_player_id
    FROM staging.utr_tour_candidates
    GROUP BY source, tour_player_id
)
UPDATE staging.utr_tour_candidates c
SET player_id = a.new_player_id
FROM assigned a
WHERE c.source = a.source
  AND c.tour_player_id = a.tour_player_id;


-- Insert one master-player row per tour player.
INSERT INTO core.players (
    player_id,
    full_name,
    country
)
SELECT DISTINCT ON (player_id)
    player_id,
    full_name,
    country
FROM staging.utr_tour_candidates
WHERE player_id IS NOT NULL
ORDER BY player_id
ON CONFLICT (player_id) DO NOTHING;


-- Insert ATP/WTA source identifiers.
INSERT INTO core.player_identifiers (
    player_id,
    source,
    source_player_id
)
SELECT DISTINCT
    player_id,
    source,
    tour_player_id
FROM staging.utr_tour_candidates
WHERE player_id IS NOT NULL
ON CONFLICT (source, source_player_id) DO NOTHING;


-- Attach UTR identifiers to the same master players.
INSERT INTO core.player_identifiers (
    player_id,
    source,
    source_player_id
)
SELECT DISTINCT
    player_id,
    'UTR',
    utr_id
FROM staging.utr_tour_candidates
WHERE player_id IS NOT NULL
ON CONFLICT (source, source_player_id) DO NOTHING;


-- Validation.
SELECT
    source,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT utr_id) AS unique_utr_ids,
    COUNT(DISTINCT tour_player_id) AS unique_tour_players,
    COUNT(DISTINCT player_id) AS unique_player_ids
FROM staging.utr_tour_candidates
GROUP BY source
ORDER BY source;
-- 8.  Match Remaining ATP/WTA Players to ITF Masters
-- Using Exact Normalized Name + Country
-- ============================================================
-- IMPORTANT:
-- This is supporting identity evidence only.
-- Explicit organisation-ID cross-references are stronger.
--
-- A match is accepted only when:
--   1. ATP/WTA source player is not already mapped.
--   2. Normalized full name matches exactly.
--   3. Country matches exactly.
--   4. The ATP/WTA player has only one possible ITF master.
--   5. The ITF master has only one possible ATP/WTA source player.
--
-- Current validated dataset:
--   ATP: 163 matches
--   WTA: 183 matches
--   Total: 346
-- ============================================================

DROP TABLE IF EXISTS staging.atp_wta_itf_name_country_matches;

CREATE TABLE staging.atp_wta_itf_name_country_matches AS

WITH unmatched_tour AS (
    SELECT
        a.source,
        a.source_player_id,
        a.full_name,
        a.country
    FROM staging.atp_wta_player_lookup a
    LEFT JOIN core.player_identifiers pi
        ON pi.source = a.source
       AND pi.source_player_id = a.source_player_id
    WHERE pi.identifier_id IS NULL
),

candidate_matches AS (
    SELECT
        a.source,
        a.source_player_id,
        a.full_name AS source_name,
        a.country AS source_country,
        i.player_id AS master_player_id,
        i.full_name AS master_name,
        i.country AS master_country
    FROM unmatched_tour a
    JOIN staging.itf_player_map i
        ON LOWER(TRIM(a.full_name)) = LOWER(TRIM(i.full_name))
       AND UPPER(TRIM(a.country)) = UPPER(TRIM(i.country))
    WHERE a.full_name IS NOT NULL
      AND TRIM(a.full_name) <> ''
      AND a.country IS NOT NULL
      AND TRIM(a.country) <> ''
      AND i.full_name IS NOT NULL
      AND TRIM(i.full_name) <> ''
      AND i.country IS NOT NULL
      AND TRIM(i.country) <> ''
),

unique_source_matches AS (
    SELECT source, source_player_id
    FROM candidate_matches
    GROUP BY source, source_player_id
    HAVING COUNT(DISTINCT master_player_id) = 1
),

unique_master_matches AS (
    SELECT master_player_id
    FROM candidate_matches
    GROUP BY master_player_id
    HAVING COUNT(
        DISTINCT source || ':' || source_player_id
    ) = 1
)

SELECT
    c.source,
    c.source_player_id,
    c.source_name,
    c.source_country,
    c.master_player_id,
    c.master_name,
    c.master_country
FROM candidate_matches c
JOIN unique_source_matches s
    ON s.source = c.source
   AND s.source_player_id = c.source_player_id
JOIN unique_master_matches m
    ON m.master_player_id = c.master_player_id;


-- Attach ATP/WTA identifiers to the existing ITF master players.
INSERT INTO core.player_identifiers (
    player_id,
    source,
    source_player_id
)
SELECT
    master_player_id,
    source,
    source_player_id
FROM staging.atp_wta_itf_name_country_matches
ON CONFLICT (source, source_player_id) DO NOTHING;


-- Validation.
SELECT
    source,
    COUNT(*) AS total_matches,
    COUNT(DISTINCT source_player_id) AS unique_source_players,
    COUNT(DISTINCT master_player_id) AS unique_master_players
FROM staging.atp_wta_itf_name_country_matches
GROUP BY source
ORDER BY source;
-- ============================================================
-- 9. Create Source-Only Master Players for Remaining ATP/WTA IDs
-- ============================================================
-- After stronger cross-source identity evidence has been used,
-- any ATP/WTA source ID that still has no master-player mapping
-- is preserved as its own master player.
--
-- This avoids incorrectly merging players based only on similar
-- names or countries.
-- ============================================================

DROP TABLE IF EXISTS staging.atp_wta_unmatched_players;

CREATE TABLE staging.atp_wta_unmatched_players AS
SELECT
    a.source,
    a.source_player_id,
    a.full_name,
    a.country,
    NULL::bigint AS player_id
FROM staging.atp_wta_player_lookup a
LEFT JOIN core.player_identifiers pi
    ON pi.source = a.source
   AND pi.source_player_id = a.source_player_id
WHERE pi.identifier_id IS NULL;


-- Assign a new internal master player ID.
UPDATE staging.atp_wta_unmatched_players
SET player_id = nextval('core.players_player_id_seq')
WHERE player_id IS NULL;


-- Insert master players.
INSERT INTO core.players (
    player_id,
    full_name,
    country
)
SELECT
    player_id,
    full_name,
    country
FROM staging.atp_wta_unmatched_players
ON CONFLICT (player_id) DO NOTHING;


-- Insert ATP/WTA source identifiers.
INSERT INTO core.player_identifiers (
    player_id,
    source,
    source_player_id
)
SELECT
    player_id,
    source,
    source_player_id
FROM staging.atp_wta_unmatched_players
ON CONFLICT (source, source_player_id) DO NOTHING;


-- Validation.
SELECT
    u.source,
    COUNT(*) AS staged_players,
    COUNT(pi.identifier_id) AS identifiers_in_core
FROM staging.atp_wta_unmatched_players u
LEFT JOIN core.player_identifiers pi
    ON pi.source = u.source
   AND pi.source_player_id = u.source_player_id
   AND pi.player_id = u.player_id
GROUP BY u.source
ORDER BY u.source;
-- ============================================================
-- 10. Isolate Unresolved UTR Identity Conflicts
-- ============================================================
-- Only UTR IDs that remain unmapped after all stronger
-- cross-source matching are considered here.
--
-- If the same remaining UTR source ID is associated with more
-- than one distinct non-empty player name across snapshots,
-- it is treated as an identity conflict.
--
-- These IDs are deliberately NOT converted into master players
-- automatically because one source ID may contain records for
-- different people.
-- ============================================================

DROP TABLE IF EXISTS staging.utr_name_conflicts;

CREATE TABLE staging.utr_name_conflicts AS
SELECT
    p.source_player_id AS utr_id,
    COUNT(
        DISTINCT LOWER(TRIM(p.full_name))
    ) FILTER (
        WHERE p.full_name IS NOT NULL
          AND TRIM(p.full_name) <> ''
    ) AS distinct_names
FROM staging.player_source_records p
LEFT JOIN core.player_identifiers pi
    ON pi.source = 'UTR'
   AND pi.source_player_id = p.source_player_id
WHERE p.source = 'UTR'
  AND p.source_player_id IS NOT NULL
  AND pi.identifier_id IS NULL
GROUP BY p.source_player_id
HAVING COUNT(
    DISTINCT LOWER(TRIM(p.full_name))
) FILTER (
    WHERE p.full_name IS NOT NULL
      AND TRIM(p.full_name) <> ''
) > 1;


-- Validation.
SELECT
    COUNT(*) AS unresolved_utr_name_conflicts
FROM staging.utr_name_conflicts;
-- ============================================================
-- 11. Create Source-Only Master Players for Clean Remaining UTR IDs
-- ============================================================
-- After all stronger cross-source matching has been exhausted,
-- remaining UTR IDs can be preserved as source-only master
-- players only when they are not part of the unresolved
-- UTR name-conflict set.
--
-- Each clean UTR source ID receives one internal player_id.
-- ============================================================

DROP TABLE IF EXISTS staging.utr_unmatched_clean_players;

CREATE TABLE staging.utr_unmatched_clean_players AS
SELECT
    u.source_player_id,
    u.full_name,
    u.country,
    u.birth_date,
    NULL::bigint AS player_id
FROM staging.utr_player_lookup_v2 u
LEFT JOIN core.player_identifiers pi
    ON pi.source = 'UTR'
   AND pi.source_player_id = u.source_player_id
LEFT JOIN staging.utr_name_conflicts c
    ON c.utr_id = u.source_player_id
WHERE pi.identifier_id IS NULL
  AND c.utr_id IS NULL;


-- Assign one new internal master player ID to each clean UTR ID.
UPDATE staging.utr_unmatched_clean_players
SET player_id = nextval('core.players_player_id_seq')
WHERE player_id IS NULL;


-- Insert master player records.
INSERT INTO core.players (
    player_id,
    full_name,
    country,
    birth_year
)
SELECT
    player_id,
    full_name,
    country,
    EXTRACT(YEAR FROM birth_date)::integer
FROM staging.utr_unmatched_clean_players
ON CONFLICT (player_id) DO NOTHING;


-- Insert corresponding UTR identifiers.
INSERT INTO core.player_identifiers (
    player_id,
    source,
    source_player_id
)
SELECT
    player_id,
    'UTR',
    source_player_id
FROM staging.utr_unmatched_clean_players
ON CONFLICT (source, source_player_id) DO NOTHING;


-- Validation.
SELECT
    COUNT(*) AS clean_utr_candidates,
    COUNT(DISTINCT source_player_id) AS unique_utr_ids,
    COUNT(DISTINCT player_id) AS unique_player_ids,
    COUNT(*) FILTER (WHERE player_id IS NULL) AS missing_player_ids
FROM staging.utr_unmatched_clean_players;
-- ============================================================
-- 12. Final Player Identity Validation
-- ============================================================
-- Final source-identifier coverage after identity processing.
--
-- For the current supplied dataset:
--   ATP:  3,282 / 3,282 mapped
--   WTA:  2,110 / 2,110 mapped
--   ITF:  9,887 / 9,887 mapped
--   UTR: 110,084 / 111,143 mapped
--
-- The remaining 1,059 UTR IDs contain conflicting player-name
-- information across snapshots and are intentionally left
-- unresolved rather than forcing an unreliable identity match.
-- ============================================================

SELECT
    source,
    COUNT(DISTINCT source_player_id) AS mapped_source_ids,
    COUNT(DISTINCT player_id) AS master_players
FROM core.player_identifiers
GROUP BY source
ORDER BY source;


-- Confirm unresolved UTR conflict count.
SELECT
    COUNT(*) AS unresolved_utr_conflicts
FROM staging.utr_name_conflicts

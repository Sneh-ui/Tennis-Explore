-- ============================================================
-- Tennis EXPLORE
-- Tennis Australia Athlete Data Integration
-- ============================================================
--
-- Purpose:
-- Integrate the athlete data supplied directly by Tennis
-- Australia into the structured player database.
--
-- The supplied athlete data contains confirmed player identity
-- information including professional tour, ITF and UTR IDs.
--
-- All supplied identifiers are retained in the integrated
-- player identity model. The broader ATP/WTA/ITF/UTR datasets
-- provide additional player coverage and ranking/rating history.
--
-- Multiple identifiers supplied for the same TA athlete belong
-- to the same master player.
-- ===========================================================
-- Integration principles:
--   1. Preserve already-correct master player identities.
--   2. Add missing identifiers supplied by Tennis Australia.
--   3. Consolidate master records where TA explicitly confirms
--      that multiple source IDs belong to the same athlete.
--   4. Do not infer additional relationships from name alone.
--   5. Preserve TA-only identifiers even when no ranking record
--      exists for that identifier in the supplied source data.
--
-- ============================================================


-- ============================================================
-- 1. Validate Tennis Australia Reference
-- ============================================================

SELECT
    COUNT(*) AS total_ta_athletes,
    COUNT(*) FILTER (WHERE pro_id IS NOT NULL) AS with_pro_id,
    COUNT(*) FILTER (WHERE itf_id IS NOT NULL) AS with_itf_id,
    COUNT(*) FILTER (WHERE cardinality(utr_ids) > 0) AS with_utr_id
FROM core.ta_athletes;
-- ============================================================
-- 2. Normalize Tennis Australia Player Identifiers
-- ============================================================
-- Convert the TA athlete reference into one row per identifier.
--
-- Example:
-- Adam Walton | ATP | ATPW09E
-- Adam Walton | ITF | 800400063
-- Adam Walton | UTR | 3086941
-- ============================================================
-- Drop dependent views first so this file can be rerun safely.
DROP VIEW IF EXISTS staging.ta_split_master_players;
DROP VIEW IF EXISTS staging.ta_identifier_comparison;
DROP VIEW IF EXISTS staging.ta_player_identifiers;

CREATE VIEW staging.ta_player_identifiers AS

-- Professional tour identifiers
SELECT
    ta_athlete_id,
    athlete_name,
    dob,
    state,
    program,
    CASE
        WHEN UPPER(pro_id) LIKE 'ATP%' THEN 'ATP'
        WHEN UPPER(pro_id) LIKE 'WTA%' THEN 'WTA'
    END AS source,
    pro_id AS source_player_id
FROM core.ta_athletes
WHERE pro_id IS NOT NULL
  AND TRIM(pro_id) <> ''

UNION ALL

-- ITF identifiers
SELECT
    ta_athlete_id,
    athlete_name,
    dob,
    state,
    program,
    'ITF' AS source,
    itf_id AS source_player_id
FROM core.ta_athletes
WHERE itf_id IS NOT NULL
  AND TRIM(itf_id) <> ''

UNION ALL

-- UTR identifiers
SELECT
    ta.ta_athlete_id,
    ta.athlete_name,
    ta.dob,
    ta.state,
    ta.program,
    'UTR' AS source,
    utr_id AS source_player_id
FROM core.ta_athletes ta
CROSS JOIN LATERAL unnest(ta.utr_ids) AS utr_id
WHERE utr_id IS NOT NULL
  AND TRIM(utr_id) <> '';


-- Validate normalized identifier records.

SELECT
    source,
    COUNT(*) AS identifier_count,
    COUNT(DISTINCT source_player_id) AS unique_identifiers
FROM staging.ta_player_identifiers
GROUP BY source
ORDER BY source;
-- ============================================================
-- 3. Compare TA Identifiers with Current Master Player Model
-- ============================================================
-- Check whether every identifier supplied by Tennis Australia
-- already exists in core.player_identifiers and, where it does,
-- which master player it currently belongs to.
--
-- This section is validation only. No player data is changed.
-- ============================================================

DROP VIEW IF EXISTS staging.ta_identifier_comparison;

CREATE VIEW staging.ta_identifier_comparison AS
SELECT
    ta.ta_athlete_id,
    ta.athlete_name,
    ta.dob,
    ta.state,
    ta.program,
    ta.source,
    ta.source_player_id,
    pi.player_id AS current_player_id,
    CASE
        WHEN pi.player_id IS NULL THEN 'MISSING'
        ELSE 'FOUND'
    END AS identifier_status
FROM staging.ta_player_identifiers ta
LEFT JOIN core.player_identifiers pi
    ON pi.source = ta.source
   AND pi.source_player_id = ta.source_player_id;


-- Overall identifier coverage

SELECT
    source,
    COUNT(*) AS ta_identifiers,
    COUNT(*) FILTER (
        WHERE identifier_status = 'FOUND'
    ) AS already_in_core,
    COUNT(*) FILTER (
        WHERE identifier_status = 'MISSING'
    ) AS missing_from_core
FROM staging.ta_identifier_comparison
GROUP BY source
ORDER BY source;


-- Overall total

SELECT
    COUNT(*) AS total_ta_identifiers,
    COUNT(*) FILTER (
        WHERE identifier_status = 'FOUND'
    ) AS already_in_core,
    COUNT(*) FILTER (
        WHERE identifier_status = 'MISSING'
    ) AS missing_from_core
FROM staging.ta_identifier_comparison;
-- ============================================================
-- 4. Detect TA Athletes Split Across Master Players
-- ============================================================
-- Tennis Australia may supply multiple identifiers for one
-- athlete. All identifiers supplied for the same athlete must
-- ultimately belong to one master player.
--
-- Identify athletes whose currently-existing identifiers point
-- to more than one core.players player_id.
-- ============================================================

DROP VIEW IF EXISTS staging.ta_split_master_players;

CREATE VIEW staging.ta_split_master_players AS
SELECT
    ta_athlete_id,
    athlete_name,
    COUNT(DISTINCT current_player_id) AS current_master_count,
    ARRAY_AGG(
        DISTINCT current_player_id
        ORDER BY current_player_id
    ) FILTER (
        WHERE current_player_id IS NOT NULL
    ) AS current_player_ids
FROM staging.ta_identifier_comparison
GROUP BY
    ta_athlete_id,
    athlete_name
HAVING COUNT(DISTINCT current_player_id) > 1;


-- Show every split athlete.

SELECT
    ta_athlete_id,
    athlete_name,
    current_master_count,
    current_player_ids
FROM staging.ta_split_master_players
ORDER BY athlete_name;
-- Show the exact identifiers currently attached to each
-- split master player.

SELECT
    c.athlete_name,
    c.source,
    c.source_player_id,
    c.current_player_id
FROM staging.ta_identifier_comparison c
JOIN staging.ta_split_master_players s
    ON s.ta_athlete_id = c.ta_athlete_id
WHERE c.current_player_id IS NOT NULL
ORDER BY
    c.athlete_name,
    c.current_player_id,
    c.source,
    c.source_player_id;
-- ============================================================
-- 5. Define Canonical Master Players for Split TA Athletes
-- ============================================================
-- Tennis Australia confirms that the identifiers listed for
-- each athlete belong to the same player.
--
-- For split athletes, retain one existing master player and
-- consolidate the other TA-confirmed identifiers into it.
--
-- No core player records are changed in this section.
-- ============================================================

DROP TABLE IF EXISTS staging.ta_master_consolidation;

CREATE TABLE staging.ta_master_consolidation (
    ta_athlete_id BIGINT PRIMARY KEY,
    athlete_name TEXT NOT NULL,
    keep_player_id BIGINT NOT NULL,
    merge_player_id BIGINT NOT NULL
);

INSERT INTO staging.ta_master_consolidation (
    ta_athlete_id,
    athlete_name,
    keep_player_id,
    merge_player_id
)
VALUES
    (4,  'Emerson Jones',        3461,   23657),
    (85, 'Roman Puthiaparampil', 109956, 110773),
    (97, 'Zach Viiala',          13434,  106943);


-- Validate the consolidation plan against core.players.

SELECT
    c.athlete_name,
    c.keep_player_id,
    kp.full_name AS keep_player_name,
    c.merge_player_id,
    mp.full_name AS merge_player_name
FROM staging.ta_master_consolidation c
JOIN core.players kp
    ON kp.player_id = c.keep_player_id
JOIN core.players mp
    ON mp.player_id = c.merge_player_id
ORDER BY c.athlete_name;
-- ============================================================
-- 6. Check References Before Master Player Consolidation
-- ============================================================
-- Before consolidating duplicate master players, identify all
-- foreign-key relationships that reference core.players.
--
-- This is validation only. No data is changed.
-- ============================================================

SELECT
    tc.table_schema,
    tc.table_name,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
   AND tc.constraint_schema = kcu.constraint_schema
JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
   AND ccu.constraint_schema = tc.constraint_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND ccu.table_schema = 'core'
  AND ccu.table_name = 'players'
  AND ccu.column_name = 'player_id'
ORDER BY
    tc.table_schema,
    tc.table_name,
    kcu.column_name;
-- ============================================================
-- 7. Validate Records Before TA Master Consolidation
-- ============================================================
-- Check identifiers and ranking snapshots attached to both the
-- retained and duplicate master player records.
--
-- Validation only. No data is changed.
-- ============================================================

-- Identifier counts for the six master player records.

SELECT
    c.athlete_name,
    pi.player_id,
    pi.source,
    pi.source_player_id
FROM staging.ta_master_consolidation c
JOIN core.player_identifiers pi
    ON pi.player_id IN (
        c.keep_player_id,
        c.merge_player_id
    )
ORDER BY
    c.athlete_name,
    pi.player_id,
    pi.source,
    pi.source_player_id;


-- Ranking rows attached to the six master player records.

SELECT
    c.athlete_name,
    rs.player_id,
    COUNT(*) AS ranking_rows
FROM staging.ta_master_consolidation c
JOIN core.ranking_snapshots rs
    ON rs.player_id IN (
        c.keep_player_id,
        c.merge_player_id
    )
GROUP BY
    c.athlete_name,
    rs.player_id
ORDER BY
    c.athlete_name,
    rs.player_id;
-- ============================================================
-- 8. Consolidate Split TA Master Players
-- ============================================================
-- Tennis Australia confirms that the identifiers supplied for
-- each athlete belong to the same player.
--
-- Move identifiers from the duplicate master player to the
-- retained master player, then remove the duplicate master.
-- ============================================================

BEGIN;

-- Move identifiers from duplicate master players to the
-- retained master players.

UPDATE core.player_identifiers pi
SET player_id = c.keep_player_id
FROM staging.ta_master_consolidation c
WHERE pi.player_id = c.merge_player_id;


-- Safety support for future reruns if ranking history has
-- already been loaded.

UPDATE core.ranking_snapshots rs
SET player_id = c.keep_player_id
FROM staging.ta_master_consolidation c
WHERE rs.player_id = c.merge_player_id;


-- Remove duplicate master player records after all references
-- have been transferred.

DELETE FROM core.players p
USING staging.ta_master_consolidation c
WHERE p.player_id = c.merge_player_id;


COMMIT;


-- Validate the consolidated TA athletes.

SELECT
    ta.athlete_name,
    COUNT(DISTINCT pi.player_id) AS master_player_count,
    ARRAY_AGG(
        DISTINCT pi.player_id
        ORDER BY pi.player_id
    ) AS player_ids,
    COUNT(*) AS identifiers_currently_in_core
FROM staging.ta_player_identifiers ta
JOIN core.player_identifiers pi
    ON pi.source = ta.source
   AND pi.source_player_id = ta.source_player_id
WHERE ta.ta_athlete_id IN (4, 85, 97)
GROUP BY
    ta.ta_athlete_id,
    ta.athlete_name
ORDER BY ta.athlete_name;
-- ============================================================
-- 9. Resolve Existing Master Player for Each TA Athlete
-- ============================================================
-- After consolidation, determine which TA athletes already
-- connect to one master player through any supplied identifier.
--
-- Athletes with no existing master will require a new
-- core.players record before their supplied identifiers can
-- be added.
-- ============================================================

DROP VIEW IF EXISTS staging.ta_athlete_master_resolution;

CREATE VIEW staging.ta_athlete_master_resolution AS
SELECT
    ta.ta_athlete_id,
    ta.athlete_name,
    ta.dob,
    ta.state,
    ta.program,
    MIN(pi.player_id) AS player_id,
    COUNT(DISTINCT pi.player_id) AS master_player_count
FROM core.ta_athletes ta
LEFT JOIN staging.ta_player_identifiers ti
    ON ti.ta_athlete_id = ta.ta_athlete_id
LEFT JOIN core.player_identifiers pi
    ON pi.source = ti.source
   AND pi.source_player_id = ti.source_player_id
GROUP BY
    ta.ta_athlete_id,
    ta.athlete_name,
    ta.dob,
    ta.state,
    ta.program;


-- Overall resolution status.

SELECT
    COUNT(*) AS total_ta_athletes,
    COUNT(*) FILTER (
        WHERE player_id IS NOT NULL
    ) AS existing_master,
    COUNT(*) FILTER (
        WHERE player_id IS NULL
    ) AS needs_new_master,
    COUNT(*) FILTER (
        WHERE master_player_count > 1
    ) AS still_split
FROM staging.ta_athlete_master_resolution;


-- Show athletes that currently have no master player.

SELECT
    ta_athlete_id,
    athlete_name,
    dob,
    state,
    program
FROM staging.ta_athlete_master_resolution
WHERE player_id IS NULL
ORDER BY athlete_name;
-- ============================================================
-- 10. Create Master Players for TA Athletes Not Yet in Core
-- ============================================================
-- Every athlete supplied by Tennis Australia must be
-- represented in the integrated master player model.
--
-- Create core.players records for TA athletes that cannot
-- currently be resolved through any existing identifier.
--
-- Full DOB, state and program remain preserved in
-- core.ta_athletes.
-- ============================================================

INSERT INTO core.players (
    full_name,
    birth_year
)
SELECT
    r.athlete_name,
    EXTRACT(YEAR FROM r.dob)::INTEGER
FROM staging.ta_athlete_master_resolution r
WHERE r.player_id IS NULL
  AND NOT EXISTS (
      SELECT 1
      FROM core.players p
      WHERE p.full_name = r.athlete_name
        AND p.birth_year = EXTRACT(YEAR FROM r.dob)::INTEGER
  );


-- Show the newly resolvable TA athletes.

SELECT
    r.ta_athlete_id,
    r.athlete_name,
    r.dob,
    p.player_id,
    p.full_name,
    p.birth_year
FROM staging.ta_athlete_master_resolution r
JOIN core.players p
    ON p.full_name = r.athlete_name
   AND p.birth_year = EXTRACT(YEAR FROM r.dob)::INTEGER
WHERE r.player_id IS NULL
ORDER BY r.athlete_name;
-- ============================================================
-- 11. Build Final TA Athlete to Master Player Mapping
-- ============================================================
-- Resolve every Tennis Australia athlete to exactly one
-- core.players master record.
--
-- Existing athletes are resolved through their identifiers.
-- TA athletes created in Section 10 are resolved using the
-- exact TA name and birth year used when creating the master.
-- ============================================================

DROP VIEW IF EXISTS staging.ta_final_player_map;

CREATE VIEW staging.ta_final_player_map AS
SELECT
    ta.ta_athlete_id,
    ta.athlete_name,
    ta.dob,
    COALESCE(
        existing.player_id,
        created.player_id
    ) AS player_id
FROM core.ta_athletes ta

LEFT JOIN LATERAL (
    SELECT MIN(pi.player_id) AS player_id
    FROM staging.ta_player_identifiers ti
    JOIN core.player_identifiers pi
        ON pi.source = ti.source
       AND pi.source_player_id = ti.source_player_id
    WHERE ti.ta_athlete_id = ta.ta_athlete_id
) existing ON TRUE

LEFT JOIN core.players created
    ON existing.player_id IS NULL
   AND created.full_name = ta.athlete_name
   AND created.birth_year = EXTRACT(YEAR FROM ta.dob)::INTEGER;


-- Every TA athlete must now resolve to one master.

SELECT
    COUNT(*) AS total_ta_athletes,
    COUNT(player_id) AS resolved_to_master,
    COUNT(*) FILTER (
        WHERE player_id IS NULL
    ) AS unresolved
FROM staging.ta_final_player_map;


-- Safety check: no TA athlete should resolve to multiple rows.

SELECT
    ta_athlete_id,
    athlete_name,
    COUNT(*) AS mapping_rows
FROM staging.ta_final_player_map
GROUP BY
    ta_athlete_id,
    athlete_name
HAVING COUNT(*) <> 1;
-- ============================================================
-- 12. Add Missing Tennis Australia Identifiers
-- ============================================================
-- Add every TA-supplied identifier that is not already present
-- in core.player_identifiers.
--
-- Each identifier is attached to the master player established
-- in staging.ta_final_player_map.
-- ============================================================

INSERT INTO core.player_identifiers (
    player_id,
    source,
    source_player_id
)
SELECT
    fm.player_id,
    ti.source,
    ti.source_player_id
FROM staging.ta_player_identifiers ti
JOIN staging.ta_final_player_map fm
    ON fm.ta_athlete_id = ti.ta_athlete_id
LEFT JOIN core.player_identifiers existing
    ON existing.source = ti.source
   AND existing.source_player_id = ti.source_player_id
WHERE existing.identifier_id IS NULL;


-- ============================================================
-- Validate complete TA identifier coverage
-- ============================================================

SELECT
    ti.source,
    COUNT(*) AS ta_identifiers,
    COUNT(pi.identifier_id) AS represented_in_core,
    COUNT(*) - COUNT(pi.identifier_id) AS missing
FROM staging.ta_player_identifiers ti
LEFT JOIN core.player_identifiers pi
    ON pi.source = ti.source
   AND pi.source_player_id = ti.source_player_id
GROUP BY ti.source
ORDER BY ti.source;


-- Overall coverage.

SELECT
    COUNT(*) AS total_ta_identifiers,
    COUNT(pi.identifier_id) AS represented_in_core,
    COUNT(*) - COUNT(pi.identifier_id) AS missing
FROM staging.ta_player_identifiers ti
LEFT JOIN core.player_identifiers pi
    ON pi.source = ti.source
   AND pi.source_player_id = ti.source_player_id;


-- Confirm that every TA athlete's supplied identifiers now
-- resolve to exactly one master player.

SELECT
    ti.ta_athlete_id,
    ti.athlete_name,
    COUNT(DISTINCT pi.player_id) AS master_player_count
FROM staging.ta_player_identifiers ti
JOIN core.player_identifiers pi
    ON pi.source = ti.source
   AND pi.source_player_id = ti.source_player_id
GROUP BY
    ti.ta_athlete_id,
    ti.athlete_name
HAVING COUNT(DISTINCT pi.player_id) <> 1;
-- ============================================================
-- 13. Final Tennis Australia Data Validation
-- ============================================================
-- Final checks for the integrated Tennis Australia athlete
-- data before moving to ranking and rating history.
-- ============================================================


-- 1. Confirm all 110 TA athletes resolve to a master player.

SELECT
    COUNT(*) AS total_ta_athletes,
    COUNT(player_id) AS resolved_to_master,
    COUNT(*) FILTER (
        WHERE player_id IS NULL
    ) AS unresolved
FROM staging.ta_final_player_map;


-- 2. Confirm all 189 supplied identifiers are represented.

SELECT
    COUNT(*) AS total_ta_identifiers,
    COUNT(pi.identifier_id) AS represented_in_core,
    COUNT(*) - COUNT(pi.identifier_id) AS missing_identifiers
FROM staging.ta_player_identifiers ti
LEFT JOIN core.player_identifiers pi
    ON pi.source = ti.source
   AND pi.source_player_id = ti.source_player_id;


-- 3. Confirm every TA athlete resolves to exactly one master.

SELECT
    ti.ta_athlete_id,
    ti.athlete_name,
    COUNT(DISTINCT pi.player_id) AS master_player_count
FROM staging.ta_player_identifiers ti
JOIN core.player_identifiers pi
    ON pi.source = ti.source
   AND pi.source_player_id = ti.source_player_id
GROUP BY
    ti.ta_athlete_id,
    ti.athlete_name
HAVING COUNT(DISTINCT pi.player_id) <> 1;


-- 4. Confirm there are no duplicate source identifiers
-- anywhere in the core identity model.

SELECT
    source,
    source_player_id,
    COUNT(*) AS duplicate_count
FROM core.player_identifiers
GROUP BY
    source,
    source_player_id
HAVING COUNT(*) > 1;


-- 5. Final TA identifier coverage by organisation.

SELECT
    ti.source,
    COUNT(*) AS supplied,
    COUNT(pi.identifier_id) AS represented,
    COUNT(*) - COUNT(pi.identifier_id) AS missing
FROM staging.ta_player_identifiers ti
LEFT JOIN core.player_identifiers pi
    ON pi.source = ti.source
   AND pi.source_player_id = ti.source_player_id
GROUP BY ti.source
ORDER BY ti.source;
-- ============================================================
-- 14. Additional Tennis Australia Athlete Identifiers
-- ============================================================
-- Cameron's updated athlete reference includes additional
-- identifiers discovered across the supplied source data:
-- TENNIS_ID, AUS_ID, LMID and TCID.
--
-- These identifiers are attached to the already-resolved
-- TA master players. No new master players are created here.
-- ============================================================

DROP TABLE IF EXISTS staging.ta_additional_identifiers;

CREATE TABLE staging.ta_additional_identifiers AS

SELECT
    m.ta_athlete_id,
    m.athlete_name,
    m.player_id,
    'TENNIS_ID'::TEXT AS source,
    a.tennis_id::TEXT AS source_player_id
FROM staging.ta_final_player_map m
JOIN core.ta_athletes a
    ON a.ta_athlete_id = m.ta_athlete_id
WHERE a.tennis_id IS NOT NULL

UNION ALL

SELECT
    m.ta_athlete_id,
    m.athlete_name,
    m.player_id,
    'AUS_ID',
    a.aus_id::TEXT
FROM staging.ta_final_player_map m
JOIN core.ta_athletes a
    ON a.ta_athlete_id = m.ta_athlete_id
WHERE a.aus_id IS NOT NULL

UNION ALL

SELECT
    m.ta_athlete_id,
    m.athlete_name,
    m.player_id,
    'LMID',
    a.lmid::TEXT
FROM staging.ta_final_player_map m
JOIN core.ta_athletes a
    ON a.ta_athlete_id = m.ta_athlete_id
WHERE a.lmid IS NOT NULL

UNION ALL

SELECT
    m.ta_athlete_id,
    m.athlete_name,
    m.player_id,
    'TCID',
    a.tcid::TEXT
FROM staging.ta_final_player_map m
JOIN core.ta_athletes a
    ON a.ta_athlete_id = m.ta_athlete_id
WHERE a.tcid IS NOT NULL;
-- ============================================================
-- 15. Validate and Load Additional TA Identifiers
-- ============================================================

-- Show any identifier that already exists in core but points
-- to a different master player.
SELECT
    ai.source,
    ai.source_player_id,
    ai.athlete_name,
    ai.player_id AS expected_player_id,
    pi.player_id AS existing_player_id
FROM staging.ta_additional_identifiers ai
JOIN core.player_identifiers pi
    ON pi.source = ai.source
   AND pi.source_player_id = ai.source_player_id
WHERE pi.player_id <> ai.player_id;


-- Insert the additional identifiers for the resolved TA players.
-- Existing identical identifiers are safely skipped.

INSERT INTO core.player_identifiers (
    player_id,
    source,
    source_player_id
)
SELECT
    ai.player_id,
    ai.source,
    ai.source_player_id
FROM staging.ta_additional_identifiers ai
WHERE NOT EXISTS (
    SELECT 1
    FROM core.player_identifiers pi
    WHERE pi.source = ai.source
      AND pi.source_player_id = ai.source_player_id
);
-- Confirm all additional TA identifiers are represented.

SELECT
    ai.source,
    COUNT(*) AS supplied,
    COUNT(pi.identifier_id) AS represented,
    COUNT(*) - COUNT(pi.identifier_id) AS missing
FROM staging.ta_additional_identifiers ai
LEFT JOIN core.player_identifiers pi
    ON pi.source = ai.source
   AND pi.source_player_id = ai.source_player_id
GROUP BY ai.source
ORDER BY ai.source;

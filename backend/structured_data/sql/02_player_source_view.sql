CREATE OR REPLACE VIEW staging.player_source_records AS  SELECT raw_record_id,
    source,
    snapshot_date,
        CASE
            WHEN source = ANY (ARRAY['ATP'::text, 'WTA'::text]) THEN raw_data ->> 'tourid'::text
            WHEN source = 'ITF'::text THEN raw_data ->> 'playerId'::text
            WHEN source = 'UTR'::text THEN COALESCE(NULLIF(raw_data ->> 'playerid'::text, ''::text), NULLIF(raw_data ->> 'utr_id'::text, ''::text))
            ELSE NULL::text
        END AS source_player_id,
        CASE
            WHEN source = ANY (ARRAY['ATP'::text, 'WTA'::text]) THEN TRIM(BOTH FROM concat_ws(' '::text, raw_data ->> 'firstname'::text, raw_data ->> 'lastname'::text))
            WHEN source = 'ITF'::text THEN TRIM(BOTH FROM concat_ws(' '::text, raw_data ->> 'playerGivenName'::text, raw_data ->> 'playerFamilyName'::text))
            WHEN source = 'UTR'::text THEN TRIM(BOTH FROM raw_data ->> 'name'::text)
            ELSE NULL::text
        END AS full_name,
        CASE
            WHEN source = ANY (ARRAY['ATP'::text, 'WTA'::text]) THEN raw_data ->> 'firstname'::text
            WHEN source = 'ITF'::text THEN raw_data ->> 'playerGivenName'::text
            ELSE NULL::text
        END AS first_name,
        CASE
            WHEN source = ANY (ARRAY['ATP'::text, 'WTA'::text]) THEN raw_data ->> 'lastname'::text
            WHEN source = 'ITF'::text THEN raw_data ->> 'playerFamilyName'::text
            ELSE NULL::text
        END AS last_name,
        CASE
            WHEN source = ANY (ARRAY['ATP'::text, 'WTA'::text]) THEN raw_data ->> 'nation'::text
            WHEN source = 'ITF'::text THEN raw_data ->> 'playerNationalityCode'::text
            WHEN source = 'UTR'::text THEN raw_data ->> 'country'::text
            ELSE NULL::text
        END AS country,
        CASE
            WHEN source = ANY (ARRAY['ATP'::text, 'WTA'::text]) THEN NULLIF(raw_data ->> 'dob'::text, ''::text)::date
            WHEN source = 'ITF'::text THEN
            CASE
                WHEN (raw_data ->> 'birthYear'::text) ~ '^\d{4}$'::text THEN make_date((raw_data ->> 'birthYear'::text)::integer, 1, 1)
                ELSE NULL::date
            END
            WHEN source = 'UTR'::text THEN
            CASE
                WHEN (raw_data ->> 'birthyr'::text) ~ '^\d{4}$'::text THEN make_date((raw_data ->> 'birthyr'::text)::integer, 1, 1)
                ELSE NULL::date
            END
            ELSE NULL::date
        END AS birth_date,
        CASE
            WHEN source = ANY (ARRAY['ATP'::text, 'WTA'::text]) THEN raw_data ->> 'tourid'::text
            WHEN source = 'UTR'::text THEN NULLIF(raw_data ->> 'atp_wta_id'::text, ''::text)
            ELSE NULL::text
        END AS atp_wta_id,
        CASE
            WHEN source = 'UTR'::text THEN NULLIF(raw_data ->> 'itf_id'::text, ''::text)
            ELSE NULL::text
        END AS itf_id
   FROM staging.raw_rankings;;

-- Implementation pending: member strings, original JSON text/VARIANT, and provenance.

-- One-time migration: store PARTITION_DATE as DDMMYYYY text, preserving zeros.
-- Existing DATE values are copied before replacing their column. Safe to rerun.
EXECUTE IMMEDIATE $$
DECLARE
    target_name VARCHAR;
    table_path VARCHAR;
    partition_type VARCHAR;
    has_text_column BOOLEAN;
    unsupported_type EXCEPTION (-20001, 'PARTITION_DATE must be DATE or text.');
    target_tables CURSOR FOR
        SELECT column1 AS TABLE_NAME
        FROM VALUES ('MEMBERS_RAW'), ('REDEMPTIONS_RAW'),
                    ('MEMBERS_LOAD_BUFFER'), ('REDEMPTIONS_LOAD_BUFFER');
BEGIN
    FOR target IN target_tables DO
        target_name := target.TABLE_NAME;
        table_path := 'SKYPOINTS.RAW.' || target_name;

        SELECT
            MAX(IFF(COLUMN_NAME = 'PARTITION_DATE', DATA_TYPE, NULL)),
            COUNT(IFF(COLUMN_NAME = 'PARTITION_DATE_TEXT', 1, NULL)) > 0
        INTO :partition_type, :has_text_column
        FROM SKYPOINTS.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'RAW' AND TABLE_NAME = :target_name
          AND COLUMN_NAME IN ('PARTITION_DATE', 'PARTITION_DATE_TEXT');

        IF (partition_type IS NULL AND has_text_column) THEN
            -- Resume a conversion interrupted before its final rename.
            ALTER TABLE IDENTIFIER(:table_path)
                RENAME COLUMN PARTITION_DATE_TEXT TO PARTITION_DATE;
        ELSEIF (partition_type IS NULL) THEN
            ALTER TABLE IDENTIFIER(:table_path)
                ADD COLUMN PARTITION_DATE VARCHAR(8);
        ELSEIF (partition_type = 'DATE') THEN
            ALTER TABLE IDENTIFIER(:table_path)
                ADD COLUMN IF NOT EXISTS PARTITION_DATE_TEXT VARCHAR(8);
            UPDATE IDENTIFIER(:table_path)
                SET PARTITION_DATE_TEXT = TO_CHAR(PARTITION_DATE, 'DDMMYYYY');
            ALTER TABLE IDENTIFIER(:table_path) DROP COLUMN PARTITION_DATE;
            ALTER TABLE IDENTIFIER(:table_path)
                RENAME COLUMN PARTITION_DATE_TEXT TO PARTITION_DATE;
        ELSEIF (partition_type NOT IN ('TEXT', 'VARCHAR')) THEN
            RAISE unsupported_type;
        END IF;
    END FOR;

    -- Backfill previously loaded RAW rows without changing assigned values.
    UPDATE SKYPOINTS.RAW.MEMBERS_RAW AS raw
    SET PARTITION_DATE = TO_CHAR(batch.LOADED_AT, 'DDMMYYYY')
    FROM SKYPOINTS.RAW.BATCH_INGESTION_LOG AS batch
    WHERE raw.BATCH_ID = batch.BATCH_ID AND raw.PARTITION_DATE IS NULL;

    UPDATE SKYPOINTS.RAW.REDEMPTIONS_RAW AS raw
    SET PARTITION_DATE = TO_CHAR(batch.LOADED_AT, 'DDMMYYYY')
    FROM SKYPOINTS.RAW.BATCH_INGESTION_LOG AS batch
    WHERE raw.BATCH_ID = batch.BATCH_ID AND raw.PARTITION_DATE IS NULL;
END;
$$;

ALTER TABLE prod_productionoutput ADD COLUMN IF NOT EXISTS reason TEXT;

ALTER TABLE prod_productionmonitoring ADD COLUMN IF NOT EXISTS rework_count INT NOT NULL DEFAULT 0;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'prod_productionoutput' AND column_name = 'inspector_id'
    ) THEN
        ALTER TABLE prod_productionoutput ADD COLUMN inspector_id INT REFERENCES users(user_id) ON DELETE SET NULL;
    ELSE
        ALTER TABLE prod_productionoutput ALTER COLUMN inspector_id TYPE INT USING (
            CASE WHEN inspector_id::text ~ '^[0-9]+$' THEN inspector_id::text::int ELSE NULL END
        );
        ALTER TABLE prod_productionoutput DROP CONSTRAINT IF EXISTS fk_prod_output_inspector;
        ALTER TABLE prod_productionoutput ADD CONSTRAINT fk_prod_output_inspector FOREIGN KEY (inspector_id) REFERENCES users(user_id) ON DELETE SET NULL;
    END IF;
END $$;

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'prod_productionoutput'::regclass AND contype = 'u'
    ) LOOP
        EXECUTE 'ALTER TABLE prod_productionoutput DROP CONSTRAINT IF EXISTS ' || quote_ident(r.conname);
    END LOOP;
END $$;

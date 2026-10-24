ALTER TABLE prod_materialissuance ADD COLUMN IF NOT EXISTS recorded_by VARCHAR(100) DEFAULT 'Dave Cagalitan';
ALTER TABLE prod_productionoutput ADD COLUMN IF NOT EXISTS recorded_by VARCHAR(100) DEFAULT 'Dave Cagalitan';

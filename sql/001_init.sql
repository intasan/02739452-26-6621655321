-- Compatible existing schema. Sources: dit, nabc, talaadthai.
-- See COMMON_SCHEMA.md for units, measurement types and source date mapping.
CREATE TABLE IF NOT EXISTS agricultural_prices (
  id BIGSERIAL PRIMARY KEY,
  observation_key TEXT NOT NULL UNIQUE,
  source TEXT NOT NULL,
  source_record_id TEXT NOT NULL,
  product_name TEXT NOT NULL,
  product_code TEXT,
  province TEXT,
  market_name TEXT,
  unit TEXT NOT NULL,
  price_min NUMERIC(12,2) NOT NULL,
  price_max NUMERIC(12,2) NOT NULL,
  observed_at DATE NOT NULL,
  measurement_type TEXT NOT NULL DEFAULT 'unspecified',
  source_url TEXT NOT NULL,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT ck_prices CHECK (price_min >= 0 AND price_max >= price_min)
);
CREATE INDEX IF NOT EXISTS ix_prices_observed ON agricultural_prices(observed_at);
CREATE TABLE IF NOT EXISTS pipeline_runs (
  run_id TEXT PRIMARY KEY,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  loaded_rows INTEGER DEFAULT 0,
  rejected_rows INTEGER DEFAULT 0,
  details JSONB NOT NULL DEFAULT '{}',
  status TEXT NOT NULL
);

-- Supabase Migration: 20260601000003_add_deliveries_table.sql
-- Create deliveries table to track pushed alerts and digests

CREATE TABLE IF NOT EXISTS deliveries (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  insight_id      UUID REFERENCES insights(id) ON DELETE CASCADE,
  channel         TEXT NOT NULL, -- 'ntfy'
  delivered_at    TIMESTAMPTZ DEFAULT now(),
  payload         JSONB,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);

DROP TRIGGER IF EXISTS update_deliveries_updated_at ON deliveries;
CREATE TRIGGER update_deliveries_updated_at
BEFORE UPDATE ON deliveries
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE deliveries ENABLE ROW LEVEL SECURITY;

-- Supabase Migration: 20260601000004_add_pipeline_health_table.sql
-- Create pipeline_health table to track per-run health score metrics

CREATE TABLE IF NOT EXISTS pipeline_health (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id               UUID REFERENCES pipeline_runs(id) ON DELETE CASCADE,
  sources_successful   INT DEFAULT 0,
  sources_total        INT DEFAULT 0,
  new_signals          INT DEFAULT 0,
  expected_new_signals INT DEFAULT 5,
  llm_success_rate     DOUBLE PRECISION DEFAULT 1.0,
  health_score         DOUBLE PRECISION NOT NULL,
  created_at           TIMESTAMPTZ DEFAULT now(),
  updated_at           TIMESTAMPTZ DEFAULT now()
);

DROP TRIGGER IF EXISTS update_pipeline_health_updated_at ON pipeline_health;
CREATE TRIGGER update_pipeline_health_updated_at
BEFORE UPDATE ON pipeline_health
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS
ALTER TABLE pipeline_health ENABLE ROW LEVEL SECURITY;

-- Add a public select policy for the read-only dashboard
DROP POLICY IF EXISTS "Allow public read-only access to pipeline_health" ON pipeline_health;
CREATE POLICY "Allow public read-only access to pipeline_health" ON pipeline_health
  FOR SELECT USING (true);

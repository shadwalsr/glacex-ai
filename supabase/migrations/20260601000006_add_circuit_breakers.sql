-- Supabase Migration: 20260601000006_add_circuit_breakers.sql
-- Create circuit_breaker_state table to track external service health across runs

CREATE TABLE IF NOT EXISTS circuit_breaker_state (
  service_name     TEXT PRIMARY KEY,
  state            TEXT NOT NULL CHECK (state IN ('closed', 'open', 'half-open')),
  failure_count    INT DEFAULT 0,
  last_failure_at  TIMESTAMPTZ,
  reset_at         TIMESTAMPTZ,
  created_at       TIMESTAMPTZ DEFAULT now(),
  updated_at       TIMESTAMPTZ DEFAULT now()
);

DROP TRIGGER IF EXISTS update_circuit_breaker_state_updated_at ON circuit_breaker_state;
CREATE TRIGGER update_circuit_breaker_state_updated_at
BEFORE UPDATE ON circuit_breaker_state
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS
ALTER TABLE circuit_breaker_state ENABLE ROW LEVEL SECURITY;

-- Allow service role to perform all actions
DROP POLICY IF EXISTS "Allow service role all on circuit_breaker_state" ON circuit_breaker_state;
CREATE POLICY "Allow service role all on circuit_breaker_state" ON circuit_breaker_state
  USING (true) WITH CHECK (true);

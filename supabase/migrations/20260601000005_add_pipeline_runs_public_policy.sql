-- Supabase Migration: 20260601000005_add_pipeline_runs_public_policy.sql
-- Add a public SELECT policy for the read-only health dashboard to access pipeline_runs

DROP POLICY IF EXISTS "Allow public read-only access to pipeline_runs" ON pipeline_runs;
CREATE POLICY "Allow public read-only access to pipeline_runs" ON pipeline_runs
  FOR SELECT USING (true);

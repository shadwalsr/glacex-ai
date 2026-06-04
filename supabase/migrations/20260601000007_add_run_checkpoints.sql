CREATE TABLE IF NOT EXISTS public.run_checkpoints (
    run_id UUID NOT NULL,
    phase TEXT NOT NULL,
    phase_started_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    phase_completed_at TIMESTAMP WITH TIME ZONE,
    docs_processed INTEGER DEFAULT 0 NOT NULL,
    PRIMARY KEY (run_id, phase)
);

ALTER TABLE public.run_checkpoints ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow service_role full access to run_checkpoints" ON public.run_checkpoints;
CREATE POLICY "Allow service_role full access to run_checkpoints"
    ON public.run_checkpoints
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

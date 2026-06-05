-- Migration: add user_feedback table for signal quality feedback loop
-- Triggered by ntfy.sh action buttons → GitHub Actions webhook → this table.

CREATE TABLE IF NOT EXISTS public.user_feedback (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL REFERENCES public.articles(id) ON DELETE CASCADE,
    rating     TEXT NOT NULL CHECK (rating IN ('good', 'noise')),
    rated_at   TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,

    -- One feedback rating per article (idempotent upserts; last-writer-wins)
    CONSTRAINT user_feedback_article_id_unique UNIQUE (article_id)
);

-- Ensure unique constraint and foreign key constraint exist even if table existed before
ALTER TABLE public.user_feedback
  DROP CONSTRAINT IF EXISTS fk_user_feedback_article,
  DROP CONSTRAINT IF EXISTS user_feedback_article_id_unique;

ALTER TABLE public.user_feedback
  ADD CONSTRAINT fk_user_feedback_article FOREIGN KEY (article_id) REFERENCES public.articles(id) ON DELETE CASCADE,
  ADD CONSTRAINT user_feedback_article_id_unique UNIQUE (article_id);

CREATE INDEX IF NOT EXISTS idx_user_feedback_rated_at ON public.user_feedback (rated_at);
CREATE INDEX IF NOT EXISTS idx_user_feedback_rating   ON public.user_feedback (rating);

ALTER TABLE public.user_feedback ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow service_role full access to user_feedback" ON public.user_feedback;
CREATE POLICY "Allow service_role full access to user_feedback"
    ON public.user_feedback
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

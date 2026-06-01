-- Supabase Migration: 20260601000010_add_web_app_policies.sql
-- Exposes database tables read-only to the public/anon role for the web explorer
-- Enables user feedback submission from the browser dashboard

-- 1. Enable SELECT on articles
DROP POLICY IF EXISTS "Allow public read-only access to articles" ON articles;
CREATE POLICY "Allow public read-only access to articles" ON articles
  FOR SELECT USING (true);

-- 2. Enable SELECT on classifications
DROP POLICY IF EXISTS "Allow public read-only access to classifications" ON classifications;
CREATE POLICY "Allow public read-only access to classifications" ON classifications
  FOR SELECT USING (true);

-- 3. Enable SELECT on insights
DROP POLICY IF EXISTS "Allow public read-only access to insights" ON insights;
CREATE POLICY "Allow public read-only access to insights" ON insights
  FOR SELECT USING (true);

-- 4. Enable SELECT on sources
DROP POLICY IF EXISTS "Allow public read-only access to sources" ON sources;
CREATE POLICY "Allow public read-only access to sources" ON sources
  FOR SELECT USING (true);

-- 5. Enable SELECT on entities
DROP POLICY IF EXISTS "Allow public read-only access to entities" ON entities;
CREATE POLICY "Allow public read-only access to entities" ON entities
  FOR SELECT USING (true);

-- 6. Enable SELECT on article_entities
DROP POLICY IF EXISTS "Allow public read-only access to article_entities" ON article_entities;
CREATE POLICY "Allow public read-only access to article_entities" ON article_entities
  FOR SELECT USING (true);

-- 7. Configure user_feedback policies
-- Drop the restrictive or old policies if present
DROP POLICY IF EXISTS "Allow public select on user_feedback" ON user_feedback;
DROP POLICY IF EXISTS "Allow public insert on user_feedback" ON user_feedback;
DROP POLICY IF EXISTS "Allow public update on user_feedback" ON user_feedback;

-- Create policies for public access (anon role)
CREATE POLICY "Allow public select on user_feedback" ON user_feedback
  FOR SELECT USING (true);

CREATE POLICY "Allow public insert on user_feedback" ON user_feedback
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow public update on user_feedback" ON user_feedback
  FOR UPDATE USING (true) WITH CHECK (true);

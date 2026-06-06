const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

const headers = {
  apikey: SUPABASE_KEY,
  Authorization: `Bearer ${SUPABASE_KEY}`,
  "Content-Type": "application/json",
};

/**
 * Fetch articles with classifications, insights, and user_feedback joins.
 * Returns up to 100 articles sorted by scraped_at desc.
 */
export async function fetchArticles() {
  const url = `${SUPABASE_URL}/rest/v1/articles?select=*,classifications!classifications_article_id_fkey(*),insights!insights_article_id_fkey(*),user_feedback!user_feedback_article_id_fkey(rating)&order=scraped_at.desc&limit=100`;
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/**
 * Submit or upsert user feedback for an article.
 */
export async function submitFeedback(articleId, rating) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/user_feedback`, {
    method: "POST",
    headers: { ...headers, Prefer: "resolution=merge-duplicates" },
    body: JSON.stringify({ article_id: articleId, rating }),
  });
  if (!res.ok) throw new Error("Supabase rejected feedback");
}

/**
 * Search articles by ILIKE query on title and clean_text.
 */
export async function searchArticles(query) {
  const encoded = encodeURIComponent(query);
  const url = `${SUPABASE_URL}/rest/v1/articles?select=*,classifications!classifications_article_id_fkey(*),insights!insights_article_id_fkey(*),user_feedback!user_feedback_article_id_fkey(rating)&or=(title.ilike.*${encoded}*,clean_text.ilike.*${encoded}*)&limit=10`;
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error("Supabase query execution error");
  return res.json();
}

/**
 * Fetch pipeline health data joined with pipeline_runs.
 */
export async function fetchHealthData() {
  const url = `${SUPABASE_URL}/rest/v1/pipeline_health?select=*,pipeline_runs!pipeline_health_run_id_fkey(*)&order=created_at.desc&limit=20`;
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/**
 * Fetch all sources sorted by creation date.
 */
export async function fetchSources() {
  const url = `${SUPABASE_URL}/rest/v1/sources?select=*&order=created_at.asc`;
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error("Registry API failure");
  return res.json();
}

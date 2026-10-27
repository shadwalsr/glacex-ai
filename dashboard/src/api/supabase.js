import { MOCK_ARTICLES, MOCK_SOURCES, MOCK_HEALTH_DATA } from '../data/mockData';

const rawUrl = (import.meta.env.VITE_SUPABASE_URL || '').trim();
const SUPABASE_URL = rawUrl.replace(/\/rest\/v1\/?$/, '').replace(/\/+$/, '');
const SUPABASE_KEY = (import.meta.env.VITE_SUPABASE_ANON_KEY || '').trim().replace(/^['"]|['"]$/g, '');

const headers = {
  apikey: SUPABASE_KEY,
  Authorization: `Bearer ${SUPABASE_KEY}`,
  "Content-Type": "application/json",
};

const LOCAL_STORAGE_FEEDBACK_KEY = 'glacex_user_feedback';

/**
 * Retrieve user feedback from localStorage.
 */
function getLocalFeedbackMap() {
  try {
    const raw = localStorage.getItem(LOCAL_STORAGE_FEEDBACK_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

/**
 * Apply local feedback overrides to an array of articles.
 */
function applyLocalFeedback(articles) {
  const feedbackMap = getLocalFeedbackMap();
  return articles.map((article) => {
    if (feedbackMap[article.id]) {
      return {
        ...article,
        user_feedback: [{ rating: feedbackMap[article.id] }],
      };
    }
    return article;
  });
}

/**
 * Check if remote Supabase connection parameters are present.
 */
export function isDataLakeConfigured() {
  return Boolean(SUPABASE_URL && SUPABASE_KEY);
}

export function getSupabaseUrl() {
  return SUPABASE_URL;
}

/**
 * Fetch articles with classifications, insights, and user_feedback joins.
 * Automatically falls back to high-signal curated intelligence corpus if Supabase is unreachable.
 */
export async function fetchArticles() {
  if (!isDataLakeConfigured()) {
    console.warn('[GlaceX Data Lake] No Supabase credentials configured; using offline intelligence corpus.');
    return {
      data: applyLocalFeedback(MOCK_ARTICLES),
      isOffline: true,
      error: 'Unconfigured Supabase credentials in .env',
    };
  }

  const url = `${SUPABASE_URL}/rest/v1/articles?select=*,classifications!classifications_article_id_fkey(*),insights!insights_article_id_fkey(*),user_feedback!user_feedback_article_id_fkey(rating)&order=scraped_at.desc&limit=100`;

  try {
    // 6-second timeout to avoid long hanging states
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);

    const res = await fetch(url, { headers, signal: controller.signal });
    clearTimeout(timeoutId);

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const errJson = await res.json();
        if (errJson?.message) {
          detail = errJson.message;
        }
      } catch (_parseErr) {
        // Fall back to default HTTP status text
      }
      throw new Error(detail);
    }

    const json = await res.json();
    return {
      data: applyLocalFeedback(json),
      isOffline: false,
      error: null,
    };
  } catch (err) {
    const reason = err.name === 'AbortError' ? 'Connection timed out' : err.message;
    console.warn(`[GlaceX Data Lake] Live Supabase connection failed (${reason}). Activating offline intelligence corpus.`);
    return {
      data: applyLocalFeedback(MOCK_ARTICLES),
      isOffline: true,
      error: reason,
    };
  }
}

/**
 * Submit or upsert user feedback for an article.
 * Persists locally and syncs to Supabase when reachable.
 */
export async function submitFeedback(articleId, rating) {
  // Always persist locally
  try {
    const feedbackMap = getLocalFeedbackMap();
    feedbackMap[articleId] = rating;
    localStorage.setItem(LOCAL_STORAGE_FEEDBACK_KEY, JSON.stringify(feedbackMap));
  } catch (err) {
    console.error('Failed to save feedback to localStorage:', err);
  }

  // If Supabase is configured, attempt remote sync
  if (isDataLakeConfigured()) {
    try {
      const res = await fetch(`${SUPABASE_URL}/rest/v1/user_feedback`, {
        method: 'POST',
        headers: { ...headers, Prefer: 'resolution=merge-duplicates' },
        body: JSON.stringify({ article_id: articleId, rating }),
      });
      if (!res.ok) {
        console.warn('Supabase remote feedback rejected:', res.status);
      }
    } catch (err) {
      console.warn('Supabase offline: Feedback cached locally.', err.message);
    }
  }
}

/**
 * Search articles by ILIKE query on title and clean_text.
 * Falls back to in-memory search across the offline corpus.
 */
export async function searchArticles(query) {
  const trimmed = query.trim().toLowerCase();

  if (isDataLakeConfigured()) {
    try {
      const encoded = encodeURIComponent(query);
      const url = `${SUPABASE_URL}/rest/v1/articles?select=*,classifications!classifications_article_id_fkey(*),insights!insights_article_id_fkey(*),user_feedback!user_feedback_article_id_fkey(rating)&or=(title.ilike.*${encoded}*,clean_text.ilike.*${encoded}*)&limit=10`;
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      const res = await fetch(url, { headers, signal: controller.signal });
      clearTimeout(timeoutId);

      if (res.ok) {
        const json = await res.json();
        return applyLocalFeedback(json);
      }
    } catch (err) {
      console.warn('[GlaceX Terminal] Remote search failed, falling back to local corpus query:', err.message);
    }
  }

  // In-memory fallback search
  const localArticles = applyLocalFeedback(MOCK_ARTICLES);
  return localArticles.filter((a) => {
    const titleMatch = a.title && a.title.toLowerCase().includes(trimmed);
    const textMatch = a.clean_text && a.clean_text.toLowerCase().includes(trimmed);
    const ins = Array.isArray(a.insights) ? a.insights[0] : a.insights;
    const tagMatch = ins?.tags && ins.tags.some((t) => t.toLowerCase().includes(trimmed));
    const entityMatch = ins?.related_entities && ins.related_entities.some((e) => e.toLowerCase().includes(trimmed));
    return titleMatch || textMatch || tagMatch || entityMatch;
  });
}

/**
 * Fetch pipeline health data joined with pipeline_runs.
 * Falls back to telemetry mock data when Supabase is unreachable.
 */
export async function fetchHealthData() {
  if (isDataLakeConfigured()) {
    try {
      const url = `${SUPABASE_URL}/rest/v1/pipeline_health?select=*,pipeline_runs!pipeline_health_run_id_fkey(*)&order=created_at.desc&limit=20`;
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      const res = await fetch(url, { headers, signal: controller.signal });
      clearTimeout(timeoutId);

      if (res.ok) {
        return await res.json();
      }
    } catch (err) {
      console.warn('[GlaceX Health] Remote telemetry unavailable, serving cached operational telemetry:', err.message);
    }
  }

  return MOCK_HEALTH_DATA;
}

/**
 * Fetch all sources sorted by creation date.
 * Falls back to configured sources registry when Supabase is unreachable.
 */
export async function fetchSources() {
  if (isDataLakeConfigured()) {
    try {
      const url = `${SUPABASE_URL}/rest/v1/sources?select=*&order=created_at.asc`;
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      const res = await fetch(url, { headers, signal: controller.signal });
      clearTimeout(timeoutId);

      if (res.ok) {
        return await res.json();
      }
    } catch (err) {
      console.warn('[GlaceX Sources] Remote source registry unavailable, serving configured inputs:', err.message);
    }
  }

  return MOCK_SOURCES;
}

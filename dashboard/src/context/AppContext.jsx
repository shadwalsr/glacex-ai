import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { fetchArticles as apiFetchArticles, submitFeedback as apiSubmitFeedback, getSupabaseUrl } from '../api/supabase';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [articles, setArticles] = useState([]);
  const [articlesLoading, setArticlesLoading] = useState(true);
  const [articlesError, setArticlesError] = useState(null);
  const [isOffline, setIsOffline] = useState(false);
  const [connectionError, setConnectionError] = useState(null);
  const [drawerArticle, setDrawerArticle] = useState(null);

  const loadArticles = useCallback(async () => {
    setArticlesLoading(true);
    try {
      const res = await apiFetchArticles();
      setArticles(res.data || []);
      setIsOffline(res.isOffline);
      setConnectionError(res.error);
      setArticlesError(null);
    } catch (err) {
      console.error('Fatal article load exception:', err);
      setArticlesError(err.message || 'Fatal data lake exception');
    } finally {
      setArticlesLoading(false);
    }
  }, []);

  // Fetch articles on mount
  useEffect(() => {
    loadArticles();
  }, [loadArticles]);

  const openDrawer = useCallback(
    (articleId) => {
      const article = articles.find((a) => a.id === articleId);
      if (article) {
        setDrawerArticle(article);
        document.body.style.overflow = 'hidden';
      }
    },
    [articles]
  );

  const closeDrawer = useCallback(() => {
    setDrawerArticle(null);
    document.body.style.overflow = '';
  }, []);

  const updateArticleFeedback = useCallback(async (articleId, rating) => {
    // Optimistic UI update
    setArticles((prev) =>
      prev.map((a) =>
        a.id === articleId
          ? { ...a, user_feedback: [{ rating }] }
          : a
      )
    );
    if (drawerArticle && drawerArticle.id === articleId) {
      setDrawerArticle((prev) => ({ ...prev, user_feedback: [{ rating }] }));
    }
    await apiSubmitFeedback(articleId, rating);
  }, [drawerArticle]);

  return (
    <AppContext.Provider
      value={{
        articles,
        setArticles,
        articlesLoading,
        articlesError,
        isOffline,
        connectionError,
        supabaseUrl: getSupabaseUrl(),
        drawerArticle,
        openDrawer,
        closeDrawer,
        updateArticleFeedback,
        refetchArticles: loadArticles,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within AppProvider');
  return context;
}

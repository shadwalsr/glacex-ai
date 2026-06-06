import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { fetchArticles as apiFetchArticles } from '../api/supabase';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [articles, setArticles] = useState([]);
  const [articlesLoading, setArticlesLoading] = useState(true);
  const [articlesError, setArticlesError] = useState(null);
  const [drawerArticle, setDrawerArticle] = useState(null);

  // Fetch articles on mount
  useEffect(() => {
    apiFetchArticles()
      .then((data) => {
        setArticles(data);
        setArticlesLoading(false);
      })
      .catch((err) => {
        setArticlesError(err.message);
        setArticlesLoading(false);
      });
  }, []);

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

  const updateArticleFeedback = useCallback((articleId, rating) => {
    setArticles((prev) =>
      prev.map((a) =>
        a.id === articleId
          ? { ...a, user_feedback: [{ rating }] }
          : a
      )
    );
  }, []);

  const refetchArticles = useCallback(async () => {
    setArticlesLoading(true);
    try {
      const data = await apiFetchArticles();
      setArticles(data);
      setArticlesError(null);
    } catch (err) {
      setArticlesError(err.message);
    } finally {
      setArticlesLoading(false);
  return (
    <AppContext.Provider
      value={{
        articles,
        setArticles,
        articlesLoading,
        articlesError,
        drawerArticle,
        openDrawer,
        closeDrawer,
        updateArticleFeedback,
        refetchArticles,
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

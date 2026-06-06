import { useState, useCallback } from 'react';
import { searchArticles as apiSearch } from '../api/supabase';

export function useTerminalSearch() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [resultCount, setResultCount] = useState(null);

  const search = useCallback(async (query) => {
    if (!query.trim()) {
      setError('Empty semantic query payload supplied.');
      setResults([]);
      setResultCount(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await apiSearch(query);
      setResults(data);
      setResultCount(data.length);
    } catch (err) {
      setError(err.message);
      setResults([]);
      setResultCount(null);
    } finally {
      setLoading(false);
    }
  }, []);

  return { results, loading, error, resultCount, search };
}

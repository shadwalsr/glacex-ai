import { useState, useEffect, useCallback } from 'react';
import { fetchSources as apiFetchSources } from '../api/supabase';

export function useSources(shouldFetch) {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const result = await apiFetchSources();
      setSources(result);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (shouldFetch) fetch();
  }, [shouldFetch, fetch]);

  return { sources, loading, error, refetch: fetch };
}

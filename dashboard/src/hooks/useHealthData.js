import { useState, useEffect, useCallback } from 'react';
import { fetchHealthData as apiFetchHealthData } from '../api/supabase';

export function useHealthData(shouldFetch) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const result = await apiFetchHealthData();
      setData(result);
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

  return { data, loading, error, refetch: fetch };
}

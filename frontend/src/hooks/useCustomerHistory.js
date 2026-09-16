import { useEffect, useState } from 'react';
import { API_BASE } from '../config';

// Shared fetch/loading-state plumbing for CustomerScoreHistoryChart and
// CustomerRiskScoreHistoryChart - same shape (a per-customer time series keyed off
// `customerId`/`refreshKey`), different endpoint and units.
export function useCustomerHistory(customerId, path, refreshKey = 0) {
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);
  // Which fetch the above state belongs to; while it doesn't match the current
  // request, the caller shows a loading placeholder. Avoids an explicit
  // setLoading(true) at the top of the effect.
  const [loadedFor, setLoadedFor] = useState(null);
  const requestKey = customerId ? `${path}:${refreshKey}` : null;
  const loading = customerId != null && loadedFor !== requestKey;

  useEffect(() => {
    if (!customerId) return;

    const controller = new AbortController();

    fetch(`${API_BASE}${path}`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
        return res.json();
      })
      .then((json) => {
        setData(Array.isArray(json) ? json : []);
        setError(null);
        setLoadedFor(requestKey);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError(err.message);
          setLoadedFor(requestKey);
        }
      });

    return () => controller.abort();
  }, [customerId, path, refreshKey, requestKey]);

  return { data, loading, error };
}

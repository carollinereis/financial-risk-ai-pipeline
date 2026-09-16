import { useEffect, useState } from 'react';
import { API_BASE } from '../config';

// Top-N default-risk / largest-loan clients plus portfolio averages - shared by
// the portfolio view's Top 5 lists and the customer view's vs-portfolio comparison.
export function usePortfolioHighlights(refreshKey = 0) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/dashboard/portfolio-highlights`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`GET /api/dashboard/portfolio-highlights -> ${res.status}`);
        return res.json();
      })
      .then(setData)
      .catch((err) => {
        if (err.name !== 'AbortError') setError(err.message);
      });
    return () => controller.abort();
  }, [refreshKey]);

  return { data, loading: !data && !error, error };
}

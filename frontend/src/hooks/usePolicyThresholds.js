import { useEffect, useState } from 'react';
import { API_BASE } from '../config';

// The enforced underwriting thresholds (src/domain/policy.py), for drawing real
// policy-gate reference lines on charts instead of an invented number.
export function usePolicyThresholds() {
  const [thresholds, setThresholds] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/dashboard/policy-reference`, { signal: controller.signal })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setThresholds(data?.thresholds ?? null))
      .catch((err) => {
        if (err.name !== 'AbortError') setThresholds(null);
      });
    return () => controller.abort();
  }, []);

  return thresholds;
}

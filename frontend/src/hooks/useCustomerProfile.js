import { useEffect, useState } from 'react';
import { API_BASE } from '../config';

// Sanitized customer profile fields (the same shape the profile drawer and the
// applicant card both render): masked PII, demographics, and the live XGBoost
// default probability.
export function useCustomerProfile(customerId) {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!customerId) return;

    const controller = new AbortController();

    fetch(`${API_BASE}/customers/${customerId}`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`GET /customers/${customerId} -> ${res.status}`);
        return res.json();
      })
      .then(setProfile)
      .catch((err) => {
        if (err.name !== 'AbortError') {
          console.error('Failed to load customer profile:', err);
          setError(err.message);
        }
      });

    return () => controller.abort();
  }, [customerId]);

  return { profile, error };
}

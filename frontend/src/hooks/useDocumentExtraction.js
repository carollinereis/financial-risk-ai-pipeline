import { useEffect, useRef, useState } from 'react';
import { API_BASE } from '../config';

// One LLM call in json mode, faster than the 3-call committee, but polled the
// same way so a page refresh never blocks on it.
const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 60 * 1000;

// Loads the customer's most recent saved extraction and exposes the one handler
// that runs a fresh extraction of their own document. Fully independent of
// useCommitteeAudit - a separate task table, a separate endpoint family, and it
// never talks to the committee's /customers/{id}/audit routes.
export function useDocumentExtraction(customerId) {
  const [extraction, setExtraction] = useState(null);
  const [loadingSaved, setLoadingSaved] = useState(true);
  const [loading, setLoading] = useState(false);
  const [taskStatus, setTaskStatus] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!customerId) return;

    const controller = new AbortController();

    // A plain Postgres read: no LLM call, so the last extraction is on screen
    // immediately. An empty list simply means none has been run yet.
    fetch(`${API_BASE}/customers/${customerId}/documents`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`GET /customers/${customerId}/documents -> ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (data.length > 0) setExtraction(data[0]);
        setLoadingSaved(false);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          console.error('Failed to load saved extractions:', err);
          setLoadingSaved(false);
        }
      });

    return () => controller.abort();
  }, [customerId]);

  // Same double-submit guard as useCommitteeAudit: a ref, not `loading` state,
  // since two click events fired back-to-back can both read `loading` as false.
  const runningRef = useRef(false);
  const pollRef = useRef(null);

  useEffect(() => () => clearInterval(pollRef.current), []);

  const finishRun = () => {
    runningRef.current = false;
    setLoading(false);
  };

  const pollTask = (taskId, deadline) => {
    fetch(`${API_BASE}/documents/tasks/${taskId}`)
      .then((res) => {
        if (!res.ok) throw new Error(`GET /documents/tasks/${taskId} -> ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setTaskStatus(data.status);

        if (data.status === 'COMPLETED') {
          clearInterval(pollRef.current);
          setExtraction(data.result);
          finishRun();
        } else if (data.status === 'FAILED') {
          clearInterval(pollRef.current);
          setError(data.error || 'The extraction failed to complete.');
          finishRun();
        } else if (Date.now() > deadline) {
          clearInterval(pollRef.current);
          setError('The extraction is taking longer than expected. Try again shortly.');
          finishRun();
        }
      })
      .catch((err) => {
        clearInterval(pollRef.current);
        console.error('Task polling error:', err);
        setError(err.message);
        finishRun();
      });
  };

  const runExtraction = () => {
    if (!customerId || runningRef.current) return;
    runningRef.current = true;
    setLoading(true);
    setError(null);
    setTaskStatus('PENDING');

    fetch(`${API_BASE}/customers/${customerId}/documents/extract`, { method: 'POST' })
      .then((res) => {
        if (!res.ok) {
          throw new Error(`POST /customers/${customerId}/documents/extract -> ${res.status}`);
        }
        return res.json();
      })
      .then(({ task_id }) => {
        const deadline = Date.now() + POLL_TIMEOUT_MS;
        pollRef.current = setInterval(() => pollTask(task_id, deadline), POLL_INTERVAL_MS);
      })
      .catch((err) => {
        console.error('Extraction error:', err);
        setError(err.message);
        finishRun();
      });
  };

  return { extraction, loadingSaved, loading, taskStatus, error, runExtraction };
}

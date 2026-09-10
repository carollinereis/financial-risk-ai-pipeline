import { useEffect, useRef, useState } from 'react';
import { API_BASE } from '../config';

// The committee takes up to ~90s (3 sequential LLM calls); poll rather than block.
const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 3 * 60 * 1000;
// How long the "Audit complete: X" confirmation stays up before it clears itself.
const CONFIRMATION_MS = 8000;

// Loads the saved committee transcript for a customer and exposes the one
// handler that runs a fresh audit. Shared by the applicant card, the agent
// recommendations panel, and the full-report drawer so there is exactly one
// place that talks to POST /customers/{id}/audit - never a second orchestration
// path, and never a duplicated poll loop that could drift from this one.
export function useCommitteeAudit(customerId, onAuditComplete) {
  const [audit, setAudit] = useState(null);
  // Distinguishes a replayed transcript from one produced by the run just made,
  // so callers can state which the underwriter is looking at.
  const [auditSource, setAuditSource] = useState(null);
  const [loadingSaved, setLoadingSaved] = useState(true);
  const [loading, setLoading] = useState(false);
  const [taskStatus, setTaskStatus] = useState(null);
  const [auditError, setAuditError] = useState(null);
  // The decision from the run that just finished, shown as a brief confirmation
  // and then cleared - null once dismissed, on a new run, or on unmount.
  const [justCompleted, setJustCompleted] = useState(null);

  useEffect(() => {
    if (!customerId) return;

    const controller = new AbortController();

    // A plain DuckDB read: opening a file never spends an LLM call, so the
    // committee's last verdict is on screen immediately. A 404 simply means
    // this client has not been through the committee yet.
    fetch(`${API_BASE}/customers/${customerId}/audit`, { signal: controller.signal })
      .then((res) => {
        if (res.status === 404) return null;
        if (!res.ok) throw new Error(`GET /customers/${customerId}/audit -> ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (data) {
          setAudit(data);
          setAuditSource('saved');
        }
        setLoadingSaved(false);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          console.error('Failed to load saved audit:', err);
          setLoadingSaved(false);
        }
      });

    return () => controller.abort();
  }, [customerId]);

  // A ref, not the `loading` state, guards against a double submit: two click
  // events fired back-to-back can both read `loading` as false if the second
  // fires before React commits the first's re-render. The ref is set the
  // instant the first click is accepted, so the second sees it immediately.
  const runningRef = useRef(false);
  const pollRef = useRef(null);
  const confirmationRef = useRef(null);

  // Cleared on unmount so a stale poll or confirmation timer never fires after
  // the caller unmounts (customer views remount per client via `key`).
  useEffect(
    () => () => {
      clearInterval(pollRef.current);
      clearTimeout(confirmationRef.current);
    },
    [],
  );

  const finishRun = () => {
    runningRef.current = false;
    setLoading(false);
  };

  const pollTask = (taskId, deadline) => {
    fetch(`${API_BASE}/tasks/${taskId}`)
      .then((res) => {
        if (!res.ok) throw new Error(`GET /tasks/${taskId} -> ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setTaskStatus(data.status);

        if (data.status === 'COMPLETED') {
          clearInterval(pollRef.current);
          setAudit(data.result);
          setAuditSource('fresh');
          finishRun();
          setJustCompleted(data.result?.decision ?? null);
          clearTimeout(confirmationRef.current);
          confirmationRef.current = setTimeout(() => setJustCompleted(null), CONFIRMATION_MS);
          // An audit writes decision_status, so the aggregate views are now stale.
          onAuditComplete?.();
        } else if (data.status === 'FAILED') {
          clearInterval(pollRef.current);
          setAuditError(data.error || 'The audit failed to complete.');
          finishRun();
        } else if (Date.now() > deadline) {
          clearInterval(pollRef.current);
          setAuditError('The audit is taking longer than expected. Try again shortly.');
          finishRun();
        }
      })
      .catch((err) => {
        clearInterval(pollRef.current);
        console.error('Task polling error:', err);
        setAuditError(err.message);
        finishRun();
      });
  };

  const runAudit = () => {
    if (!customerId || runningRef.current) return;
    runningRef.current = true;
    setLoading(true);
    setAuditError(null);
    setJustCompleted(null);
    clearTimeout(confirmationRef.current);
    setTaskStatus('PENDING');

    fetch(`${API_BASE}/customers/${customerId}/audit`, { method: 'POST' })
      .then((res) => {
        if (!res.ok) throw new Error(`POST /customers/${customerId}/audit -> ${res.status}`);
        return res.json();
      })
      .then(({ task_id }) => {
        const deadline = Date.now() + POLL_TIMEOUT_MS;
        pollRef.current = setInterval(() => pollTask(task_id, deadline), POLL_INTERVAL_MS);
      })
      .catch((err) => {
        console.error('Audit error:', err);
        setAuditError(err.message);
        finishRun();
      });
  };

  return { audit, auditSource, loadingSaved, loading, taskStatus, auditError, justCompleted, runAudit };
}

// src/components/ExceptionQueue.jsx
import { useCallback, useEffect, useMemo, useState } from 'react';
import { API_BASE } from '../config';

const STATUS_COLORS = {
  APPROVED: 'var(--status-approved)',
  REJECTED: 'var(--status-rejected)',
  'MANUAL REVIEW REQUIRED': 'var(--status-review)',
};

// Only these two are accepted by the override endpoint; a human ruling is
// always a definitive approve or reject, never another deferral.
const OVERRIDE_ACTIONS = [
  { status: 'APPROVED', label: 'Approve' },
  { status: 'REJECTED', label: 'Reject' },
];

// The name is kept for the session so working a queue does not mean retyping a
// signature per row. It is self-declared — the dashboard has no authentication,
// so this attributes an override without authenticating it.
const UNDERWRITER_KEY = 'underwriter-name';

const currency = (value) =>
  `$${(value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

function VoteSummary({ votes = [] }) {
  return (
    <div style={tableStyles.votes}>
      {votes.map((vote) => (
        <div key={`${vote.application_id}-${vote.agent_name}`}>
          <span style={tableStyles.vote}>
            <span style={tableStyles.voteAgent}>{vote.agent_name.replace(/ Agent$/, '')}</span>
            <strong>{vote.decision}</strong>
          </span>
          {/* Deterministic policy can overrule an agent, leaving the vote at odds
              with the agent's own prose. Saying why is the difference between a
              guardrail and an apparent defect. */}
          {vote.verdict_basis && (
            <div style={tableStyles.voteBasis}>{vote.verdict_basis}</div>
          )}
        </div>
      ))}
    </div>
  );
}

export function ExceptionQueue({ onInspectCustomer, onDecisionRecorded, refreshKey = 0 }) {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [draftId, setDraftId] = useState(null);
  const [draft, setDraft] = useState({ status: null, rationale: '' });
  const [underwriter, setUnderwriter] = useState(() => {
    try {
      return localStorage.getItem(UNDERWRITER_KEY) || '';
    } catch {
      return '';
    }
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  // No synchronous setLoading here: the initial state already covers first paint,
  // and a refetch after an override keeps the table on screen instead of flickering.
  const loadQueue = useCallback((signal) => {
    return fetch(`${API_BASE}/api/dashboard/hitl-queue`, { signal })
      .then((res) => {
        if (!res.ok) throw new Error(`GET /api/dashboard/hitl-queue -> ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setQueue(Array.isArray(data) ? data : []);
        setError(null);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError(err.message);
          setLoading(false);
        }
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadQueue(controller.signal);
    return () => controller.abort();
  }, [loadQueue, refreshKey]);

  const openDraft = (applicationId, status) => {
    setDraftId(applicationId);
    setDraft({ status, rationale: '' });
    setSubmitError(null);
  };

  const cancelDraft = () => {
    setDraftId(null);
    setDraft({ status: null, rationale: '' });
    setSubmitError(null);
  };

  const submitOverride = (applicationId) => {
    const rationale = draft.rationale.trim();
    // The API rejects an empty rationale; block here so the underwriter keeps
    // what they typed instead of losing it to a 422.
    if (!rationale) {
      setSubmitError('A rationale is required for the audit trail.');
      return;
    }

    const signature = underwriter.trim();
    // The API rejects an anonymous override; an audit trail without a name on it
    // answers "what" but never "who", which is the question an auditor asks.
    if (!signature) {
      setSubmitError('An underwriter name is required so the override is attributable.');
      return;
    }

    setSubmitting(true);
    fetch(`${API_BASE}/api/dashboard/override/${applicationId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: draft.status, rationale, underwriter: signature }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const detail = await res.json().catch(() => null);
          throw new Error(detail?.detail || `PATCH override -> ${res.status}`);
        }
        return res.json();
      })
      .then(() => {
        setSubmitting(false);
        try {
          localStorage.setItem(UNDERWRITER_KEY, signature);
        } catch {
          // A locked-down browser costs a retype, never the ruling itself.
        }
        cancelDraft();
        // Refetch rather than splice locally: the row leaves the queue because
        // the server stamped overridden_at, so the server is the authority.
        loadQueue();
        onDecisionRecorded?.();
      })
      .catch((err) => {
        setSubmitError(err.message);
        setSubmitting(false);
      });
  };

  const heading = useMemo(
    () => `⚠️ Exception Queue — Human-in-the-Loop Review${queue.length ? ` (${queue.length})` : ''}`,
    [queue.length],
  );

  return (
    <div style={tableStyles.card}>
      <h3 style={tableStyles.heading}>{heading}</h3>

      {loading ? (
        <div style={tableStyles.empty}>Loading exception queue...</div>
      ) : error ? (
        <div style={tableStyles.errorBox}>Failed to load exception queue: {error}</div>
      ) : queue.length === 0 ? (
        <div style={tableStyles.empty}>
          No exceptions pending. Every evaluated application reached a unanimous committee decision.
        </div>
      ) : (
        <table style={tableStyles.table}>
          <thead>
            <tr>
              <th style={tableStyles.th}>App</th>
              <th style={tableStyles.th}>Client</th>
              <th style={tableStyles.th}>Requested</th>
              <th style={tableStyles.th}>Current Status</th>
              <th style={tableStyles.th}>Agent Votes</th>
              <th style={tableStyles.th}>Action</th>
            </tr>
          </thead>
          <tbody>
            {queue.map((row) => (
              <tr key={row.application_id} style={tableStyles.tr}>
                <td style={tableStyles.td}>#{row.application_id}</td>
                <td style={tableStyles.td}>
                  <button
                    type="button"
                    onClick={() => onInspectCustomer(row.customer_id)}
                    style={tableStyles.inspectBtn}
                  >
                    {row.full_name} ➔
                  </button>
                  <div style={tableStyles.subtle}>Client #{row.customer_id}</div>
                </td>
                <td style={tableStyles.td}>{currency(row.requested_amount)}</td>
                <td style={tableStyles.td}>
                  <span
                    style={{
                      ...tableStyles.badge,
                      background: STATUS_COLORS[row.decision_status] || 'var(--text-secondary)',
                    }}
                  >
                    {row.decision_status}
                  </span>
                </td>
                <td style={tableStyles.td}>
                  <VoteSummary votes={row.agent_votes} />
                </td>
                <td style={tableStyles.td}>
                  {draftId === row.application_id ? (
                    <div style={tableStyles.draft}>
                      <strong style={tableStyles.draftTitle}>
                        Override to {draft.status}
                      </strong>
                      <input
                        type="text"
                        style={tableStyles.textarea}
                        placeholder="Underwriter name (required)"
                        value={underwriter}
                        onChange={(e) => setUnderwriter(e.target.value)}
                      />
                      <textarea
                        style={tableStyles.textarea}
                        rows={3}
                        autoFocus
                        placeholder="Rationale for the audit trail (required)"
                        value={draft.rationale}
                        onChange={(e) => setDraft((d) => ({ ...d, rationale: e.target.value }))}
                      />
                      {submitError && <div style={tableStyles.submitError}>{submitError}</div>}
                      <div style={tableStyles.draftActions}>
                        <button
                          type="button"
                          style={tableStyles.confirmBtn}
                          disabled={submitting}
                          onClick={() => submitOverride(row.application_id)}
                        >
                          {submitting ? 'Saving...' : 'Confirm'}
                        </button>
                        <button
                          type="button"
                          style={tableStyles.cancelBtn}
                          disabled={submitting}
                          onClick={cancelDraft}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div style={tableStyles.actions}>
                      {OVERRIDE_ACTIONS.map((action) => (
                        <button
                          key={action.status}
                          type="button"
                          style={{
                            ...tableStyles.actionBtn,
                            borderColor: STATUS_COLORS[action.status],
                            color: STATUS_COLORS[action.status],
                          }}
                          onClick={() => openDraft(row.application_id, action.status)}
                        >
                          {action.label}
                        </button>
                      ))}
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const tableStyles = {
  card: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    padding: '20px',
    marginBottom: '24px',
  },
  heading: {
    fontSize: '14px',
    fontWeight: '600',
    color: 'var(--text-primary)',
    marginBottom: '16px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '13px',
  },
  th: {
    textAlign: 'left',
    padding: '10px',
    borderBottom: '1px solid var(--border)',
    color: 'var(--text-secondary)',
    fontSize: '11px',
    textTransform: 'uppercase',
  },
  tr: {
    borderBottom: '1px solid var(--border)',
  },
  td: {
    padding: '12px 10px',
    color: 'var(--text-primary)',
    verticalAlign: 'top',
  },
  subtle: {
    color: 'var(--text-secondary)',
    fontSize: '11px',
    marginTop: '2px',
  },
  badge: {
    padding: '3px 8px',
    borderRadius: '4px',
    color: 'var(--bg)',
    fontSize: '10px',
    fontWeight: '700',
    whiteSpace: 'nowrap',
  },
  votes: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  vote: {
    display: 'flex',
    gap: '6px',
    fontSize: '11px',
    color: 'var(--text-primary)',
  },
  voteAgent: {
    color: 'var(--text-secondary)',
    minWidth: '72px',
  },
  voteBasis: {
    color: 'var(--text-secondary)',
    fontSize: '10px',
    lineHeight: 1.4,
    marginLeft: '78px',
    marginBottom: '4px',
    maxWidth: '320px',
  },
  inspectBtn: {
    background: 'transparent',
    border: 'none',
    padding: 0,
    color: 'var(--accent)',
    fontWeight: '600',
    cursor: 'pointer',
    fontSize: '13px',
  },
  actions: {
    display: 'flex',
    gap: '6px',
  },
  actionBtn: {
    background: 'transparent',
    border: '1px solid',
    borderRadius: '6px',
    padding: '4px 10px',
    fontSize: '11px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  draft: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    minWidth: '220px',
  },
  draftTitle: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
  },
  textarea: {
    background: 'var(--bg)',
    border: '1px solid var(--border)',
    borderRadius: '6px',
    color: 'var(--text-primary)',
    padding: '6px 8px',
    fontSize: '12px',
    fontFamily: 'inherit',
    resize: 'vertical',
  },
  draftActions: {
    display: 'flex',
    gap: '6px',
  },
  confirmBtn: {
    background: 'var(--accent)',
    border: 'none',
    borderRadius: '6px',
    color: 'var(--bg)',
    padding: '5px 12px',
    fontSize: '11px',
    fontWeight: '700',
    cursor: 'pointer',
  },
  cancelBtn: {
    background: 'transparent',
    border: '1px solid var(--border)',
    borderRadius: '6px',
    color: 'var(--text-secondary)',
    padding: '5px 12px',
    fontSize: '11px',
    cursor: 'pointer',
  },
  submitError: {
    color: 'var(--status-rejected)',
    fontSize: '11px',
  },
  empty: {
    color: 'var(--text-secondary)',
    fontSize: '13px',
    padding: '16px 0',
  },
  errorBox: {
    color: 'var(--status-rejected)',
    fontSize: '13px',
    padding: '16px 0',
  },
};

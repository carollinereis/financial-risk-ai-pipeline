// src/components/CustomerRegistry.jsx
import { useEffect, useMemo, useState } from 'react';

const VERDICT_COLORS = {
  APPROVED: 'var(--status-approved)',
  REJECTED: 'var(--status-rejected)',
  'MANUAL REVIEW REQUIRED': 'var(--status-review)',
};

// The registry ranks by what an underwriter scans for first: unreviewed files,
// then the ones the committee could not settle, then everything already ruled on.
const STANDING_ORDER = {
  PENDING: 0,
  'MANUAL REVIEW REQUIRED': 1,
  REJECTED: 2,
  APPROVED: 3,
};

const FILTERS = [
  { key: 'ALL', label: 'All' },
  { key: 'ANALYZED', label: 'Analyzed' },
  { key: 'PENDING', label: 'Not analyzed' },
];

// Matches the drawer's threshold: below this the saved and live probabilities
// are the same score with rounding noise between them.
const DRIFT_EPSILON = 0.005;

const hasDrifted = (row) =>
  row.audit_risk_score != null &&
  row.risk_score != null &&
  Math.abs(row.risk_score - row.audit_risk_score) > DRIFT_EPSILON;

const formatDate = (value) => {
  if (!value) return '—';
  const parsed = new Date(value.replace(' ', 'T'));
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
};

// The roster is fetched once in App and shared with the navbar search, so this
// panel renders whatever the dashboard already holds rather than refetching.
export function CustomerRegistry({
  open,
  customers = [],
  loading = false,
  error = null,
  onClose,
  onInspectCustomer,
}) {
  const rows = customers;
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('ALL');

  // Esc closes the panel; the overlay click alone is not reachable by keyboard.
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') onClose?.();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return rows
      .filter((row) => {
        if (filter === 'ANALYZED' && !row.has_saved_audit) return false;
        if (filter === 'PENDING' && row.has_saved_audit) return false;
        if (!needle) return true;
        return (
          String(row.customer_id).includes(needle) ||
          (row.full_name || '').toLowerCase().includes(needle)
        );
      })
      .sort((a, b) => {
        const rankA = STANDING_ORDER[a.has_saved_audit ? a.decision_status : 'PENDING'] ?? 4;
        const rankB = STANDING_ORDER[b.has_saved_audit ? b.decision_status : 'PENDING'] ?? 4;
        return rankA - rankB || a.customer_id - b.customer_id;
      });
  }, [rows, query, filter]);

  if (!open) return null;

  const analyzedCount = rows.filter((row) => row.has_saved_audit).length;

  return (
    <div style={registryStyles.overlay} onClick={onClose}>
      <div
        style={registryStyles.panel}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Evaluated Customers Registry"
      >
        <div style={registryStyles.header}>
          <div>
            <h2 style={registryStyles.title}>Evaluated Customers Registry</h2>
            <span style={registryStyles.subtitle}>
              {analyzedCount} of {rows.length} customers have a saved committee audit
            </span>
          </div>
          <button onClick={onClose} style={registryStyles.closeBtn} aria-label="Close registry">
            ✕
          </button>
        </div>

        <div style={registryStyles.toolbar}>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by customer ID or name…"
            style={registryStyles.search}
          />
          <div style={registryStyles.filters}>
            {FILTERS.map((option) => (
              <button
                key={option.key}
                type="button"
                onClick={() => setFilter(option.key)}
                style={{
                  ...registryStyles.filterBtn,
                  borderColor: filter === option.key ? 'var(--accent)' : 'var(--border)',
                  color: filter === option.key ? 'var(--accent)' : 'var(--text-secondary)',
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div style={registryStyles.tableWrap}>
          {loading && <p style={registryStyles.empty}>Loading registry…</p>}
          {error && <p style={registryStyles.errorBox}>Registry unavailable: {error}</p>}

          {!loading && !error && visible.length === 0 && (
            <p style={registryStyles.empty}>No customers match this filter.</p>
          )}

          {!loading && !error && visible.length > 0 && (
            <table style={registryStyles.table}>
              <thead>
                <tr>
                  <th style={registryStyles.th}>Customer</th>
                  <th style={registryStyles.th}>Credit Score</th>
                  <th style={registryStyles.th}>CRO Final Verdict</th>
                  <th style={registryStyles.th}>Last Analyzed</th>
                  <th style={registryStyles.th}>Report</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((row) => (
                  <tr key={row.customer_id} style={registryStyles.tr}>
                    <td style={registryStyles.td}>
                      <strong>{row.full_name}</strong>
                      <div style={registryStyles.subtle}>#{row.customer_id}</div>
                    </td>
                    <td style={registryStyles.td}>{row.credit_score}</td>
                    <td style={registryStyles.td}>
                      {row.has_saved_audit ? (
                        <>
                          <span
                            style={{
                              ...registryStyles.badge,
                              background:
                                VERDICT_COLORS[row.decision_status] || 'var(--text-secondary)',
                            }}
                          >
                            {row.decision_status}
                          </span>
                          {/* Three facts that change how much weight the verdict
                              carries, none of them visible from the status alone. */}
                          {row.human_overridden && (
                            <div style={registryStyles.subtle}>
                              Override · {row.overridden_by || 'unattributed'}
                            </div>
                          )}
                          {row.committee_split && (
                            <div style={registryStyles.subtle}>Split committee</div>
                          )}
                          {hasDrifted(row) && (
                            <div style={registryStyles.drift}>
                              Model re-scored since audit
                            </div>
                          )}
                        </>
                      ) : (
                        <span style={registryStyles.subtle}>Not analyzed</span>
                      )}
                    </td>
                    <td style={registryStyles.td}>{formatDate(row.last_analyzed_at)}</td>
                    <td style={registryStyles.td}>
                      <button
                        type="button"
                        style={registryStyles.inspectBtn}
                        onClick={() => onInspectCustomer?.(row.customer_id)}
                      >
                        {row.has_saved_audit ? 'View Agent Details' : 'Open Profile'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

const registryStyles = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
    zIndex: 900,
  },
  // Sits below the customer drawer's z-index so a report opened from a row
  // reads on top of the registry rather than behind it.
  panel: {
    width: 'min(980px, 100%)',
    maxHeight: '86vh',
    display: 'flex',
    flexDirection: 'column',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    padding: '20px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    borderBottom: '1px solid var(--border)',
    paddingBottom: '12px',
  },
  title: { margin: 0, fontSize: '16px', color: 'var(--text-primary)' },
  subtitle: { fontSize: '11px', color: 'var(--text-secondary)' },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: 'var(--text-primary)',
    fontSize: '18px',
    cursor: 'pointer',
  },
  toolbar: {
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
    flexWrap: 'wrap',
    padding: '14px 0',
  },
  search: {
    flex: '1 1 240px',
    background: 'var(--bg)',
    border: '1px solid var(--border)',
    borderRadius: '6px',
    color: 'var(--text-primary)',
    padding: '8px 10px',
    fontSize: '13px',
    fontFamily: 'inherit',
  },
  filters: { display: 'flex', gap: '6px' },
  filterBtn: {
    background: 'transparent',
    border: '1px solid',
    borderRadius: '6px',
    padding: '6px 12px',
    fontSize: '11px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  tableWrap: { overflowY: 'auto', flex: 1 },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '13px' },
  th: {
    textAlign: 'left',
    padding: '10px',
    borderBottom: '1px solid var(--border)',
    color: 'var(--text-secondary)',
    fontSize: '11px',
    textTransform: 'uppercase',
    position: 'sticky',
    top: 0,
    background: 'var(--surface)',
  },
  tr: { borderBottom: '1px solid var(--border)' },
  td: { padding: '12px 10px', color: 'var(--text-primary)', verticalAlign: 'top' },
  subtle: { color: 'var(--text-secondary)', fontSize: '11px', marginTop: '2px' },
  drift: { color: 'var(--status-review)', fontSize: '11px', marginTop: '2px', fontWeight: '600' },
  badge: {
    display: 'inline-block',
    padding: '3px 8px',
    borderRadius: '4px',
    color: 'var(--bg)',
    fontSize: '10px',
    fontWeight: '700',
    whiteSpace: 'nowrap',
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
  empty: { color: 'var(--text-secondary)', fontSize: '13px', padding: '16px 0' },
  errorBox: { color: 'var(--status-rejected)', fontSize: '13px', padding: '16px 0' },
};

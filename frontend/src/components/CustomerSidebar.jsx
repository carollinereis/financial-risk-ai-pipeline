// src/components/CustomerSidebar.jsx
import { useEffect, useMemo, useRef, useState } from 'react';

const VERDICT_COLORS = {
  APPROVED: 'var(--status-approved)',
  REJECTED: 'var(--status-rejected)',
  'MANUAL REVIEW REQUIRED': 'var(--status-review)',
};

// Same standing order and filter semantics as the Evaluated Customers Registry,
// so the two lists never disagree about what "not analyzed" or "pending" means.
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

// The customer list that drives what the main dashboard area shows. One row is
// always highlighted (or none, in portfolio view) - clicking a row, a header
// search result, or a registry "Open Profile" all set the same selection.
export function CustomerSidebar({
  customers = [],
  loading = false,
  error = null,
  selectedCustomerId = null,
  onSelect,
  onClear,
}) {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('ALL');
  // Roving focus across the row buttons: Up/Down moves it, the browser's own
  // Enter/Space activates whichever row is focused, same division of labour
  // CustomerSearch uses for its results list. Bounded by `visible.length`
  // (a plain render-time value) rather than the ref array's own length, so
  // nothing ever mutates a ref during render.
  const rowRefs = useRef([]);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return customers
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
  }, [customers, query, filter]);

  const moveFocus = (fromIndex, delta) => {
    const count = visible.length;
    if (!count) return;
    const next = (fromIndex + delta + count) % count;
    rowRefs.current[next]?.focus();
  };

  const onListKeyDown = (event) => {
    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
    const currentIndex = rowRefs.current.findIndex((el) => el === document.activeElement);
    event.preventDefault();
    if (currentIndex === -1) {
      rowRefs.current[event.key === 'ArrowDown' ? 0 : visible.length - 1]?.focus();
      return;
    }
    moveFocus(currentIndex, event.key === 'ArrowDown' ? 1 : -1);
  };

  // A selection made elsewhere (a Top 5 name, the header search, the registry)
  // has to actually be visible here for "highlight that customer" to be true -
  // clear whatever filter/search would be hiding them. Deliberately only keyed
  // on the id, not the filter/query this itself sets, or it would refight the
  // underwriter's own filter choice on every render.
  useEffect(() => {
    if (selectedCustomerId == null) return;
    const isVisible = visible.some((c) => c.customer_id === selectedCustomerId);
    const exists = customers.some((c) => c.customer_id === selectedCustomerId);
    if (!isVisible && exists) {
      setFilter('ALL');
      setQuery('');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCustomerId]);

  // Once the selected row is actually rendered, scroll it into view.
  useEffect(() => {
    if (selectedCustomerId == null) return;
    const index = visible.findIndex((c) => c.customer_id === selectedCustomerId);
    rowRefs.current[index]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [selectedCustomerId, visible]);

  return (
    <div style={sidebarStyles.panel}>
      <div style={sidebarStyles.head}>
        <h3 style={sidebarStyles.title}>Customers</h3>
        {selectedCustomerId != null && (
          <button type="button" onClick={onClear} style={sidebarStyles.clearBtn}>
            Clear
          </button>
        )}
      </div>

      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search name or #ID..."
        style={sidebarStyles.search}
      />

      <div style={sidebarStyles.filters}>
        {FILTERS.map((option) => (
          <button
            key={option.key}
            type="button"
            onClick={() => setFilter(option.key)}
            style={{
              ...sidebarStyles.filterBtn,
              borderColor: filter === option.key ? 'var(--accent)' : 'var(--border)',
              color: filter === option.key ? 'var(--accent)' : 'var(--text-secondary)',
            }}
          >
            {option.label}
          </button>
        ))}
      </div>

      <div style={sidebarStyles.list} role="listbox" aria-label="Customers" onKeyDown={onListKeyDown}>
        {loading && <p style={sidebarStyles.empty}>Loading customers…</p>}
        {error && <p style={sidebarStyles.errorBox}>Unavailable: {error}</p>}
        {!loading && !error && visible.length === 0 && (
          <p style={sidebarStyles.empty}>No customers match this filter.</p>
        )}
        {!loading &&
          !error &&
          visible.map((row, index) => {
            const selected = row.customer_id === selectedCustomerId;
            return (
              <button
                key={row.customer_id}
                ref={(el) => {
                  rowRefs.current[index] = el;
                }}
                type="button"
                role="option"
                aria-selected={selected}
                onClick={() => onSelect?.(row.customer_id)}
                style={{
                  ...sidebarStyles.row,
                  background: selected ? 'var(--surface-hover)' : 'transparent',
                  borderColor: selected ? 'var(--accent)' : 'transparent',
                }}
              >
                <span style={sidebarStyles.identity}>
                  <span style={sidebarStyles.name}>{row.full_name}</span>
                  <span style={sidebarStyles.meta}>
                    #{row.customer_id} · Score {row.credit_score}
                  </span>
                </span>
                {row.has_saved_audit ? (
                  <span
                    style={{
                      ...sidebarStyles.badge,
                      background: VERDICT_COLORS[row.decision_status] || 'var(--text-secondary)',
                    }}
                  >
                    {row.decision_status}
                  </span>
                ) : (
                  <span style={{ ...sidebarStyles.badge, ...sidebarStyles.badgeMuted }}>
                    Not analyzed
                  </span>
                )}
              </button>
            );
          })}
      </div>
    </div>
  );
}

const sidebarStyles = {
  panel: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    padding: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    // Independent scroll region: the row list scrolls on its own while this
    // panel stays put alongside the main area as the page scrolls.
    position: 'sticky',
    top: '20px',
    maxHeight: 'calc(100vh - 40px)',
  },
  head: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  title: { margin: 0, fontSize: '14px', color: 'var(--text-primary)' },
  clearBtn: {
    background: 'transparent',
    border: '1px solid var(--border)',
    borderRadius: '6px',
    color: 'var(--text-secondary)',
    padding: '3px 8px',
    fontSize: '11px',
    cursor: 'pointer',
  },
  search: {
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
    flex: 1,
    background: 'transparent',
    border: '1px solid',
    borderRadius: '6px',
    padding: '5px 6px',
    fontSize: '10px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    overflowY: 'auto',
    minHeight: 0,
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '8px',
    padding: '8px',
    borderRadius: '6px',
    border: '1px solid transparent',
    cursor: 'pointer',
    textAlign: 'left',
    font: 'inherit',
  },
  identity: { display: 'flex', flexDirection: 'column', minWidth: 0 },
  name: {
    fontSize: '12px',
    color: 'var(--text-primary)',
    fontWeight: '600',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  meta: { fontSize: '10px', color: 'var(--text-secondary)' },
  badge: {
    padding: '2px 6px',
    borderRadius: '4px',
    color: 'var(--bg)',
    fontSize: '9px',
    fontWeight: '700',
    whiteSpace: 'nowrap',
  },
  badgeMuted: { background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-secondary)' },
  empty: { color: 'var(--text-secondary)', fontSize: '12px', padding: '10px 0' },
  errorBox: { color: 'var(--status-rejected)', fontSize: '12px', padding: '10px 0' },
};

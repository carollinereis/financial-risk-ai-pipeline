// src/components/CustomerSearch.jsx
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Search } from 'lucide-react';

const MAX_RESULTS = 8;

// Ranked so the most literal reading of the query wins: an exact ID beats an ID
// prefix, which beats a name that starts with the term, which beats a substring.
const RANK_EXACT_ID = 0;
const RANK_ID_PREFIX = 1;
const RANK_NAME_PREFIX = 2;
const RANK_CONTAINS = 3;

const isMac = () =>
  typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || '');

function scoreMatch(customer, needle) {
  if (!needle) return RANK_CONTAINS;

  const id = String(customer.customer_id);
  const name = (customer.full_name || '').toLowerCase();
  // '#107' and '107' are the same query; the sigil is presentation, not data.
  const term = needle.replace(/^#/, '');

  if (id === term) return RANK_EXACT_ID;
  if (id.startsWith(term)) return RANK_ID_PREFIX;
  if (name.startsWith(term)) return RANK_NAME_PREFIX;
  if (name.includes(term) || id.includes(term)) return RANK_CONTAINS;
  return null;
}

export function CustomerSearch({ customers = [], onSelectCustomer }) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef(null);
  const containerRef = useRef(null);

  const results = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return customers
      .map((customer) => ({ customer, rank: scoreMatch(customer, needle) }))
      .filter((entry) => entry.rank !== null)
      .sort((a, b) => a.rank - b.rank || a.customer.customer_id - b.customer.customer_id)
      .slice(0, MAX_RESULTS)
      .map((entry) => entry.customer);
  }, [customers, query]);

  // Clamped on read rather than reset in an effect: a narrowing query shortens
  // the list in the same render that produced it, so the highlight can never
  // point past the end.
  const highlighted = results.length ? Math.min(activeIndex, results.length - 1) : 0;

  const focusSearch = useCallback(() => {
    setOpen(true);
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  useEffect(() => {
    const onKeyDown = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        focusSearch();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [focusSearch]);

  // Clicking anywhere else dismisses the list; blur alone would fire before the
  // click lands on a result and swallow the selection.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event) => {
      if (!containerRef.current?.contains(event.target)) setOpen(false);
    };
    window.addEventListener('mousedown', onPointerDown);
    return () => window.removeEventListener('mousedown', onPointerDown);
  }, [open]);

  const select = (customer) => {
    if (!customer) return;
    onSelectCustomer?.(customer.customer_id);
    setQuery('');
    setOpen(false);
    inputRef.current?.blur();
  };

  const onInputKeyDown = (event) => {
    if (event.key === 'Escape') {
      setOpen(false);
      inputRef.current?.blur();
      return;
    }
    if (!open && (event.key === 'ArrowDown' || event.key === 'Enter')) {
      setOpen(true);
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((i) => (results.length ? (i + 1) % results.length : 0));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((i) => (results.length ? (i - 1 + results.length) % results.length : 0));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      select(results[highlighted]);
    }
  };

  const empty = customers.length === 0;

  return (
    <div ref={containerRef} style={searchStyles.wrapper}>
      <div style={{ ...searchStyles.field, borderColor: open ? 'var(--accent)' : 'var(--border)' }}>
        <Search size={15} color="var(--text-secondary)" aria-hidden="true" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          disabled={empty}
          onChange={(e) => {
            setQuery(e.target.value);
            setActiveIndex(0);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onInputKeyDown}
          placeholder={empty ? 'No clients loaded' : 'Search client by name or #ID'}
          style={searchStyles.input}
          role="combobox"
          aria-expanded={open}
          aria-controls="client-search-results"
          aria-autocomplete="list"
          aria-label="Search clients"
        />
        <kbd style={searchStyles.shortcut}>{isMac() ? '⌘K' : 'Ctrl K'}</kbd>
      </div>

      {open && !empty && (
        <ul id="client-search-results" role="listbox" style={searchStyles.list}>
          {results.length === 0 && (
            <li style={searchStyles.noMatch}>No client matches “{query.trim()}”</li>
          )}
          {results.map((customer, index) => (
            <li
              key={customer.customer_id}
              role="option"
              aria-selected={index === highlighted}
              onMouseEnter={() => setActiveIndex(index)}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => select(customer)}
              style={{
                ...searchStyles.row,
                background: index === highlighted ? 'var(--surface-hover)' : 'transparent',
              }}
            >
              <span style={searchStyles.identity}>
                <span style={searchStyles.name}>{customer.full_name}</span>
                <span style={searchStyles.meta}>
                  #{customer.customer_id} · Score {customer.credit_score}
                </span>
              </span>
              <StatusBadge analyzed={customer.has_saved_audit} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// The badge answers the only question that changes what happens on click: is a
// saved report waiting, or will this client need a committee run first?
function StatusBadge({ analyzed }) {
  return (
    <span
      style={{
        ...searchStyles.badge,
        color: analyzed ? 'var(--status-approved)' : 'var(--status-review)',
        borderColor: analyzed ? 'var(--status-approved)' : 'var(--status-review)',
      }}
    >
      {analyzed ? 'Analyzed' : 'Not Analyzed'}
    </span>
  );
}

const searchStyles = {
  wrapper: { position: 'relative', width: 'min(320px, 40vw)' },
  field: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '8px',
    padding: '7px 10px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'border-color 120ms ease',
  },
  input: {
    flex: 1,
    minWidth: 0,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: 'var(--text-primary)',
    fontSize: '13px',
    fontFamily: 'inherit',
  },
  shortcut: {
    border: '1px solid var(--border)',
    borderRadius: '4px',
    padding: '1px 5px',
    fontSize: '10px',
    color: 'var(--text-secondary)',
    fontFamily: 'inherit',
    whiteSpace: 'nowrap',
  },
  list: {
    position: 'absolute',
    top: 'calc(100% + 6px)',
    left: 0,
    right: 0,
    margin: 0,
    padding: '4px',
    listStyle: 'none',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '8px',
    boxShadow: '0 8px 24px rgba(0,0,0,0.25)',
    zIndex: 1100,
    maxHeight: '320px',
    overflowY: 'auto',
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '10px',
    padding: '8px 10px',
    borderRadius: '6px',
    cursor: 'pointer',
  },
  identity: { display: 'flex', flexDirection: 'column', minWidth: 0 },
  name: {
    fontSize: '13px',
    color: 'var(--text-primary)',
    fontWeight: '600',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  meta: { fontSize: '11px', color: 'var(--text-secondary)' },
  badge: {
    border: '1px solid',
    borderRadius: '4px',
    padding: '2px 6px',
    fontSize: '10px',
    fontWeight: '700',
    whiteSpace: 'nowrap',
  },
  noMatch: { padding: '10px', fontSize: '12px', color: 'var(--text-secondary)' },
};

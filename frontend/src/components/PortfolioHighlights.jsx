// src/components/PortfolioHighlights.jsx
import { gridStyles } from './chartStyles';
import { useChartColors } from '../hooks/useChartColors';
import { usePortfolioHighlights } from '../hooks/usePortfolioHighlights';

const currency = (value) => `$${Math.round(value ?? 0).toLocaleString()}`;
const pct = (value) => `${((value ?? 0) * 100).toFixed(1)}%`;

// Two Top-5 rankings, each a small set of bars scaled to its own max - never
// sharing an axis with the other, since default probability and loan size are
// different units.
export function PortfolioHighlights({ refreshKey = 0, onSelectCustomer }) {
  const colors = useChartColors();
  const { data, loading, error } = usePortfolioHighlights(refreshKey);

  return (
    <>
      <RankedList
        title="Top 5 Highest Default Probability"
        loading={loading}
        error={error}
        rows={data?.top_default_risk}
        valueOf={(row) => row.risk_score}
        format={pct}
        barColor={colors.rejected}
        onSelectCustomer={onSelectCustomer}
      />
      <RankedList
        title="Top 5 Largest Requested Loans"
        loading={loading}
        error={error}
        rows={data?.top_loan_amounts}
        valueOf={(row) => row.loan_amount_requested}
        format={currency}
        barColor={colors.accent}
        onSelectCustomer={onSelectCustomer}
      />
    </>
  );
}

function RankedList({ title, loading, error, rows, valueOf, format, barColor, onSelectCustomer }) {
  const list = rows ?? [];
  const max = list.length ? Math.max(...list.map(valueOf)) : 0;

  return (
    <div style={gridStyles.card}>
      <h3 style={gridStyles.title}>{title}</h3>

      {loading ? (
        <div style={gridStyles.placeholder}>Loading...</div>
      ) : error ? (
        <div style={gridStyles.placeholderError}>Failed to load: {error}</div>
      ) : list.length === 0 ? (
        <div style={gridStyles.placeholder}>No scored customers yet</div>
      ) : (
        <div style={listStyles.wrap}>
          {list.map((row, index) => {
            const value = valueOf(row);
            const widthPct = max > 0 ? Math.max(4, Math.round((value / max) * 100)) : 0;
            return (
              <div key={row.customer_id} style={listStyles.row}>
                <span style={listStyles.rank}>{index + 1}</span>
                <div style={listStyles.body}>
                  <div style={listStyles.rowHead}>
                    <button
                      type="button"
                      className="top5-name-btn"
                      style={listStyles.name}
                      onClick={() => onSelectCustomer?.(row.customer_id)}
                    >
                      {row.full_name} <span style={listStyles.id}>#{row.customer_id}</span>
                    </button>
                    <span style={listStyles.value}>{format(value)}</span>
                  </div>
                  <div style={listStyles.track}>
                    <div style={{ ...listStyles.fill, width: `${widthPct}%`, background: barColor }} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

const listStyles = {
  wrap: { display: 'flex', flexDirection: 'column', gap: '10px' },
  row: { display: 'flex', alignItems: 'center', gap: '10px' },
  rank: {
    width: '18px',
    flexShrink: 0,
    fontSize: '11px',
    color: 'var(--text-secondary)',
    fontWeight: '700',
    textAlign: 'center',
  },
  body: { flex: 1, minWidth: 0 },
  rowHead: { display: 'flex', justifyContent: 'space-between', gap: '8px', marginBottom: '4px' },
  name: {
    fontSize: '12px',
    color: 'var(--text-primary)',
    fontWeight: '600',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  id: { color: 'var(--text-secondary)', fontWeight: '400' },
  value: { fontSize: '12px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' },
  track: { height: '6px', borderRadius: '3px', background: 'var(--surface-hover)', overflow: 'hidden' },
  fill: { height: '100%', borderRadius: '3px' },
};

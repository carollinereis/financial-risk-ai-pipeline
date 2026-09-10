// src/components/CustomerVsPortfolio.jsx
import { gridStyles } from './chartStyles';
import { useChartColors } from '../hooks/useChartColors';
import { usePortfolioHighlights } from '../hooks/usePortfolioHighlights';

// Three metrics, three different scales - each stays its own small multiple
// rather than sharing one axis (credit score, a DTI ratio, and a probability
// have nothing in common to plot together).
const METRICS = [
  {
    key: 'credit_score',
    label: 'Credit Score',
    domain: [300, 850],
    client: (profile) => profile.credit_score,
    portfolio: (avg) => avg.avg_credit_score,
    format: (v) => Math.round(v),
  },
  {
    key: 'dti',
    label: 'DTI Ratio',
    domain: [0, 1],
    client: (profile) => profile.debt_to_income_ratio,
    portfolio: (avg) => avg.avg_debt_to_income_ratio,
    format: (v) => `${(v * 100).toFixed(1)}%`,
  },
  {
    key: 'default_probability',
    label: 'Default Probability',
    domain: [0, 1],
    client: (profile) => profile.live_xgb_risk_score,
    portfolio: (avg) => avg.avg_default_probability,
    format: (v) => `${(v * 100).toFixed(1)}%`,
  },
];

export function CustomerVsPortfolio({ profile, refreshKey = 0 }) {
  const colors = useChartColors();
  const { data, loading, error } = usePortfolioHighlights(refreshKey);
  const averages = data?.portfolio_averages;

  return (
    <div style={gridStyles.card}>
      <h3 style={gridStyles.title}>Customer vs Portfolio</h3>

      <div style={compareStyles.legend}>
        <LegendSwatch color={colors.accent} label="This client" />
        <LegendSwatch color={colors.textSecondary} label="Portfolio average" />
      </div>

      {error ? (
        <div style={gridStyles.placeholderError}>Failed to load portfolio averages: {error}</div>
      ) : loading || !averages ? (
        <div style={gridStyles.placeholder}>Loading comparison...</div>
      ) : (
        <div style={compareStyles.rows}>
          {METRICS.map((metric) => {
            const clientValue = metric.client(profile);
            const portfolioValue = metric.portfolio(averages);
            const [min, max] = metric.domain;
            const span = max - min || 1;
            const clientPct = Math.min(100, Math.max(0, ((clientValue - min) / span) * 100));
            const portfolioPct = Math.min(100, Math.max(0, ((portfolioValue - min) / span) * 100));

            return (
              <div key={metric.key} style={compareStyles.row}>
                <span style={compareStyles.rowLabel}>{metric.label}</span>
                <MetricBar pct={clientPct} value={metric.format(clientValue)} color={colors.accent} />
                <MetricBar pct={portfolioPct} value={metric.format(portfolioValue)} color={colors.textSecondary} />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function LegendSwatch({ color, label }) {
  return (
    <span style={compareStyles.legendItem}>
      <span style={{ ...compareStyles.swatch, background: color }} />
      {label}
    </span>
  );
}

function MetricBar({ pct, value, color }) {
  return (
    <div style={compareStyles.barRow}>
      <div style={compareStyles.track}>
        <div style={{ ...compareStyles.fill, width: `${pct}%`, background: color }} />
      </div>
      <span style={compareStyles.barValue}>{value}</span>
    </div>
  );
}

const compareStyles = {
  legend: { display: 'flex', gap: '16px', marginBottom: '14px' },
  legendItem: { display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--text-secondary)' },
  swatch: { width: '9px', height: '9px', borderRadius: '2px', display: 'inline-block' },
  rows: { display: 'flex', flexDirection: 'column', gap: '16px' },
  row: { display: 'flex', flexDirection: 'column', gap: '4px' },
  rowLabel: { fontSize: '12px', color: 'var(--text-primary)', fontWeight: '600' },
  barRow: { display: 'flex', alignItems: 'center', gap: '8px' },
  track: { flex: 1, height: '8px', borderRadius: '4px', background: 'var(--surface-hover)', overflow: 'hidden' },
  fill: { height: '100%', borderRadius: '4px' },
  barValue: { width: '52px', textAlign: 'right', fontSize: '11px', color: 'var(--text-secondary)' },
};

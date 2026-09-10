// Shared Recharts styling for ChartsGrid.jsx and CustomerScoreHistoryChart.jsx, so a
// per-customer chart card matches the portfolio charts' look exactly.

export const tooltipStyle = (colors) => ({
  background: 'var(--surface)',
  borderColor: colors.border,
  borderRadius: '6px',
  color: colors.textPrimary,
  fontSize: '12px',
});

export const gridStyles = {
  container: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px', marginBottom: '24px' },
  card: { background: 'var(--surface)', padding: '20px', borderRadius: '8px', border: '1px solid var(--border)' },
  title: { margin: '0 0 15px 0', fontSize: '15px', color: 'var(--text-primary)', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' },
  subtitle: { fontSize: '11px', fontWeight: 400, color: 'var(--text-secondary)' },
  subtitleStack: { display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px', textAlign: 'right' },
  placeholder: { height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontSize: '13px' },
  placeholderError: { height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--status-rejected)', fontSize: '13px', textAlign: 'center', padding: '0 12px' },
};

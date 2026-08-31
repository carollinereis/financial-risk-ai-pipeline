// src/components/ChartsGrid.jsx
import { useState, useEffect, useMemo } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid } from 'recharts';
import { API_BASE } from '../config';
import { useChartColors } from '../hooks/useChartColors';

// Credit bands follow FICO ranges; every band is emitted so the axis stays stable.
const SCORE_BANDS = [
  { label: 'Poor (<580)', min: 0, max: 580 },
  { label: 'Fair (580-669)', min: 580, max: 670 },
  { label: 'Good (670-739)', min: 670, max: 740 },
  { label: 'Very Good (740-799)', min: 740, max: 800 },
  { label: 'Exceptional (800+)', min: 800, max: Infinity },
];

// Legend labels stay short; the raw status is what the API and DB agree on.
const DECISION_META = {
  APPROVED: { label: 'Approved', colorKey: 'approved' },
  REJECTED: { label: 'Rejected', colorKey: 'rejected' },
  'MANUAL REVIEW REQUIRED': { label: 'Manual Review', colorKey: 'review' },
};

const json = (res, route) => {
  if (!res.ok) throw new Error(`GET ${route} -> ${res.status}`);
  return res.json();
};

export function ChartsGrid({ customers = [], refreshKey = 0 }) {
  const colors = useChartColors();
  const [decisions, setDecisions] = useState(null);
  const [consensus, setConsensus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    const opts = { signal: controller.signal };

    Promise.all([
      fetch(`${API_BASE}/api/dashboard/decision-distribution`, opts).then((r) =>
        json(r, '/api/dashboard/decision-distribution'),
      ),
      fetch(`${API_BASE}/api/dashboard/agent-consensus`, opts).then((r) =>
        json(r, '/api/dashboard/agent-consensus'),
      ),
    ])
      .then(([decisionData, consensusData]) => {
        setDecisions(decisionData);
        setConsensus(consensusData);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [refreshKey]);

  // Portfolio outcome, read from the persisted decision_status so underwriter
  // overrides are reflected and the split ties out to the KPI approval rate.
  const decisionData = useMemo(() => {
    const rows = decisions?.distribution ?? [];
    return rows
      .filter((row) => (row.application_count ?? 0) > 0)
      .map((row) => {
        const meta = DECISION_META[row.status];
        return {
          name: meta?.label ?? row.status,
          value: row.application_count ?? 0,
          share: row.share_pct ?? 0,
          fill: colors[meta?.colorKey] || colors.accent,
        };
      });
  }, [decisions, colors]);

  const scoreDistribution = useMemo(
    () =>
      SCORE_BANDS.map((band) => ({
        band: band.label,
        count: customers.filter(
          (c) => c.credit_score >= band.min && c.credit_score < band.max,
        ).length,
      })),
    [customers],
  );

  return (
    <div style={gridStyles.container}>
      {/* 1. Agent committee consensus vs divergence */}
      <div style={gridStyles.card}>
        <h3 style={gridStyles.title}>
          Portfolio Decision Split
          <span style={gridStyles.subtitleStack}>
            {consensus ? (
              <span style={gridStyles.subtitle}>
                {consensus.consensus_rate_pct}% agent agreement · {consensus.pending_review_count} pending review
              </span>
            ) : null}
            {/* The donut covers only clients the committee has ruled on. Without the
                denominator it reads as the whole portfolio, which it is not. */}
            {decisions ? (
              <span style={gridStyles.subtitle}>
                Based on {decisions.total_applications} of {customers.length} clients analyzed
              </span>
            ) : null}
          </span>
        </h3>

        {loading ? (
          <div style={gridStyles.placeholder}>Loading decision metrics...</div>
        ) : error ? (
          <div style={gridStyles.placeholderError}>Failed to load decision data: {error}</div>
        ) : decisionData.length === 0 ? (
          <div style={gridStyles.placeholder}>No decision data available</div>
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={decisionData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={4}
                dataKey="value"
                nameKey="name"
              >
                {decisionData.map((entry) => (
                  <Cell key={entry.name} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={tooltipStyle(colors)}
                formatter={(value, name, entry) => [
                  `${value} (${entry?.payload?.share ?? 0}%)`,
                  name,
                ]}
              />
              <Legend verticalAlign="bottom" height={36} />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* 2. Credit Score Distribution (monochromatic, zero phantom bars) */}
      <div style={gridStyles.card}>
        <h3 style={gridStyles.title}>
          Credit Score Distribution
          <span style={gridStyles.subtitle}>All {customers.length} clients on file</span>
        </h3>
        {customers.length === 0 ? (
          <div style={gridStyles.placeholder}>No applicant data available</div>
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={scoreDistribution} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
              <XAxis
                dataKey="band"
                tick={{ fill: colors.textSecondary, fontSize: 10 }}
                tickFormatter={(label) => label.split(' ')[0]}
                stroke={colors.border}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fill: colors.textSecondary, fontSize: 11 }}
                stroke={colors.border}
              />
              <Tooltip cursor={{ fill: 'transparent' }} contentStyle={tooltipStyle(colors)} />
              <Bar dataKey="count" name="Applicants" fill={colors.accent} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

const tooltipStyle = (colors) => ({
  background: 'var(--surface)',
  borderColor: colors.border,
  borderRadius: '6px',
  color: colors.textPrimary,
  fontSize: '12px',
});

const gridStyles = {
  container: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' },
  card: { background: 'var(--surface)', padding: '20px', borderRadius: '8px', border: '1px solid var(--border)' },
  title: { margin: '0 0 15px 0', fontSize: '15px', color: 'var(--text-primary)', display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '10px' },
  subtitle: { fontSize: '11px', fontWeight: 400, color: 'var(--text-secondary)' },
  subtitleStack: { display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px', textAlign: 'right' },
  placeholder: { height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontSize: '13px' },
  placeholderError: { height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--status-rejected)', fontSize: '13px', textAlign: 'center', padding: '0 12px' },
};

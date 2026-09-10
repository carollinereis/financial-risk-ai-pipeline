// src/components/ChartsGrid.jsx
import { useState, useEffect, useMemo } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { gridStyles, tooltipStyle } from './chartStyles';
import { useChartColors } from '../hooks/useChartColors';
import { API_BASE } from '../config';

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

// Portfolio-level decision split. Always describes the whole analyzed slice of
// the portfolio - it never filters to a selected customer.
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

  return (
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
  );
}

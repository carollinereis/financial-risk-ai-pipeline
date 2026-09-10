// src/components/CreditScoreBandChart.jsx
import { useEffect, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { gridStyles, tooltipStyle } from './chartStyles';
import { useChartColors } from '../hooks/useChartColors';
import { API_BASE } from '../config';

// One magnitude series (average default probability), grouped by FICO tier - a
// single hue is enough, so this chart carries no legend of its own.
export function CreditScoreBandChart({ refreshKey = 0 }) {
  const colors = useChartColors();
  const [bands, setBands] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/dashboard/credit-score-bands`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`GET /api/dashboard/credit-score-bands -> ${res.status}`);
        return res.json();
      })
      .then((data) => setBands(Array.isArray(data) ? data : []))
      .catch((err) => {
        if (err.name !== 'AbortError') setError(err.message);
      });
    return () => controller.abort();
  }, [refreshKey]);

  const chartData = (bands ?? []).map((row) => ({
    band: row.band,
    range: row.range_label,
    defaultProbabilityPct: Math.round(row.avg_default_probability * 1000) / 10,
    customerCount: row.customer_count,
  }));

  return (
    <div style={gridStyles.card}>
      <h3 style={gridStyles.title}>
        Default Probability by Credit Score Band
        <span style={gridStyles.subtitle}>Portfolio-wide, by FICO tier</span>
      </h3>

      {error ? (
        <div style={gridStyles.placeholderError}>Failed to load band data: {error}</div>
      ) : !bands ? (
        <div style={gridStyles.placeholder}>Loading band data...</div>
      ) : chartData.every((row) => row.customerCount === 0) ? (
        <div style={gridStyles.placeholder}>No scored customers yet</div>
      ) : (
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
            <XAxis dataKey="band" tick={{ fill: colors.textSecondary, fontSize: 11 }} stroke={colors.border} />
            <YAxis
              domain={[0, 'dataMax']}
              tickFormatter={(v) => `${v}%`}
              tick={{ fill: colors.textSecondary, fontSize: 11 }}
              stroke={colors.border}
            />
            <Tooltip
              contentStyle={tooltipStyle(colors)}
              formatter={(value, _name, entry) => [
                `${value}% avg default probability (${entry?.payload?.customerCount ?? 0} clients)`,
                entry?.payload?.range,
              ]}
            />
            <Bar dataKey="defaultProbabilityPct" fill={colors.rejected} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

// src/components/CustomerScoreHistoryChart.jsx
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { gridStyles, tooltipStyle } from './chartStyles';
import { useChartColors } from '../hooks/useChartColors';
import { useCustomerHistory } from '../hooks/useCustomerHistory';
import { usePolicyThresholds } from '../hooks/usePolicyThresholds';

export function CustomerScoreHistoryChart({ customerId, refreshKey = 0 }) {
  const colors = useChartColors();
  const thresholds = usePolicyThresholds();
  const { data: history, loading, error } = useCustomerHistory(
    customerId,
    customerId ? `/customers/${customerId}/score-history` : null,
    refreshKey,
  );

  const latest = history.length ? history[history.length - 1] : null;

  return (
    <div style={gridStyles.card}>
      <h3 style={gridStyles.title}>
        Credit Score History
        <span style={gridStyles.subtitleStack}>
          <span style={gridStyles.subtitle}>
            {latest ? `Latest ${latest.score} · ${latest.date}` : customerId ? `Client #${customerId}` : 'No client selected'}
          </span>
          {history.length > 0 && (
            <span style={gridStyles.subtitle}>{history.length} points recorded</span>
          )}
        </span>
      </h3>

      {!customerId ? (
        <div style={gridStyles.placeholder}>Select a client to see their score history</div>
      ) : loading ? (
        <div style={gridStyles.placeholder}>Loading score history...</div>
      ) : error ? (
        <div style={gridStyles.placeholderError}>Failed to load score history: {error}</div>
      ) : history.length === 0 ? (
        <div style={gridStyles.placeholder}>No score history recorded yet</div>
      ) : (
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={history} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="creditScoreGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={colors.accent} stopOpacity={0.35} />
                <stop offset="95%" stopColor={colors.accent} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
            <XAxis dataKey="date" tick={{ fill: colors.textSecondary, fontSize: 10 }} stroke={colors.border} />
            <YAxis
              domain={[300, 850]}
              tick={{ fill: colors.textSecondary, fontSize: 11 }}
              stroke={colors.border}
            />
            <Tooltip contentStyle={tooltipStyle(colors)} />
            {thresholds && (
              <ReferenceLine
                y={thresholds.min_credit_score}
                stroke={colors.review}
                strokeDasharray="4 4"
                label={{
                  value: `Minimum policy score (${thresholds.min_credit_score})`,
                  position: 'insideTopRight',
                  fill: colors.textSecondary,
                  fontSize: 10,
                }}
              />
            )}
            <Area
              type="monotone"
              dataKey="score"
              name="Credit score"
              stroke={colors.accent}
              strokeWidth={2}
              fill="url(#creditScoreGradient)"
              dot={{ r: 3, fill: colors.accent }}
              activeDot={{ r: 5 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

// src/components/CustomerRiskScoreHistoryChart.jsx
import { useMemo } from 'react';
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

export function CustomerRiskScoreHistoryChart({ customerId, refreshKey = 0 }) {
  const colors = useChartColors();
  const thresholds = usePolicyThresholds();
  const { data: rawHistory, loading, error } = useCustomerHistory(
    customerId,
    customerId ? `/customers/${customerId}/risk-score-history` : null,
    refreshKey,
  );

  // The API returns the raw XGBoost probability (0-1); the chart reads in points (0-100).
  const history = useMemo(
    () => rawHistory.map((point) => ({ date: point.date, scorePct: point.score * 100 })),
    [rawHistory],
  );
  const latest = history.length ? history[history.length - 1] : null;
  const gatePct = thresholds ? thresholds.xgb_high_risk_threshold * 100 : null;

  return (
    <div style={gridStyles.card}>
      <h3 style={gridStyles.title}>
        Risk Score History
        <span style={gridStyles.subtitleStack}>
          <span style={gridStyles.subtitle}>
            {latest
              ? `Latest ${latest.scorePct.toFixed(2)}% · ${latest.date}`
              : customerId
                ? `Client #${customerId}`
                : 'No client selected'}
          </span>
          {history.length > 0 && (
            <span style={gridStyles.subtitle}>{history.length} recorded audit runs</span>
          )}
        </span>
      </h3>

      {!customerId ? (
        <div style={gridStyles.placeholder}>Select a client to see their risk score history</div>
      ) : loading ? (
        <div style={gridStyles.placeholder}>Loading risk score history...</div>
      ) : error ? (
        <div style={gridStyles.placeholderError}>Failed to load risk score history: {error}</div>
      ) : history.length === 0 ? (
        <div style={gridStyles.placeholder}>No audit runs recorded yet</div>
      ) : (
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={history} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="riskScoreGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={colors.rejected} stopOpacity={0.35} />
                <stop offset="95%" stopColor={colors.rejected} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
            <XAxis dataKey="date" tick={{ fill: colors.textSecondary, fontSize: 10 }} stroke={colors.border} />
            <YAxis
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
              tick={{ fill: colors.textSecondary, fontSize: 11 }}
              stroke={colors.border}
            />
            <Tooltip contentStyle={tooltipStyle(colors)} formatter={(value) => [`${value.toFixed(2)}%`, 'Risk score']} />
            {gatePct != null && (
              <ReferenceLine
                y={gatePct}
                stroke={colors.rejected}
                strokeDasharray="4 4"
                label={{
                  value: `Policy 1 gate (${gatePct.toFixed(0)}%)`,
                  position: 'insideTopRight',
                  fill: colors.textSecondary,
                  fontSize: 10,
                }}
              />
            )}
            <Area
              type="monotone"
              dataKey="scorePct"
              name="Risk score"
              stroke={colors.rejected}
              strokeWidth={2}
              fill="url(#riskScoreGradient)"
              dot={{ r: 3, fill: colors.rejected }}
              activeDot={{ r: 5 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

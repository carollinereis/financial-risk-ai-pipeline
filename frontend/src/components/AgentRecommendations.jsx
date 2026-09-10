// src/components/AgentRecommendations.jsx
import { gridStyles } from './chartStyles';

const VERDICT_COLORS = {
  APPROVE: 'var(--status-approved)',
  ALERT: 'var(--status-review)',
  REJECT: 'var(--status-rejected)',
};

const DECISION_COLORS = {
  APPROVED: 'var(--status-approved)',
  REJECTED: 'var(--status-rejected)',
  'MANUAL REVIEW REQUIRED': 'var(--status-review)',
};

// Each agent's vote plus the reasoning that produced it, read from the saved
// audit transcript - never a live agent call, so opening this panel never
// costs an LLM run. Reuses the same audit state (and the same runAudit
// handler) the applicant card's button drives, so both stay in sync.
export function AgentRecommendations({ audit }) {
  const { audit: report, loading, taskStatus, runAudit } = audit;

  return (
    <div style={gridStyles.card}>
      <h3 style={gridStyles.title}>Agent Recommendations</h3>

      {!report ? (
        <div style={panelStyles.empty}>
          <p style={panelStyles.emptyText}>
            No committee audit has been recorded for this client yet.
          </p>
          <button type="button" onClick={runAudit} disabled={loading} style={panelStyles.runBtn}>
            {loading ? (taskStatus === 'PROCESSING' ? 'Running audit…' : 'Queued…') : 'Run committee audit'}
          </button>
        </div>
      ) : (
        <div style={panelStyles.list}>
          <AgentRow label="Quantitative Agent" verdict={report.quant_verdict} basis={report.quant_basis} />
          <AgentRow label="Qualitative Agent" verdict={report.qual_verdict} basis={report.qual_basis} />
          <div style={panelStyles.finalVerdict}>
            <span style={panelStyles.finalLabel}>CRO final verdict</span>
            <span
              style={{
                ...panelStyles.finalBadge,
                background: DECISION_COLORS[report.decision] || 'var(--text-secondary)',
              }}
            >
              {report.decision}
            </span>
          </div>
          {report.cro_basis && <p style={panelStyles.basis}>{report.cro_basis}</p>}
        </div>
      )}
    </div>
  );
}

function AgentRow({ label, verdict, basis }) {
  return (
    <div style={panelStyles.row}>
      <div style={panelStyles.rowHead}>
        <span style={panelStyles.rowLabel}>{label}</span>
        {verdict && (
          <span style={{ ...panelStyles.rowBadge, color: VERDICT_COLORS[verdict] || 'var(--text-secondary)' }}>
            {verdict}
          </span>
        )}
      </div>
      {basis && <p style={panelStyles.basis}>{basis}</p>}
    </div>
  );
}

const panelStyles = {
  empty: { display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'flex-start' },
  emptyText: { fontSize: '12px', color: 'var(--text-secondary)', margin: 0 },
  runBtn: {
    background: 'var(--accent)',
    color: 'var(--bg)',
    border: 'none',
    borderRadius: '6px',
    padding: '9px 14px',
    fontSize: '12px',
    fontWeight: '700',
    cursor: 'pointer',
  },
  list: { display: 'flex', flexDirection: 'column', gap: '12px' },
  row: { borderBottom: '1px solid var(--border)', paddingBottom: '10px' },
  rowHead: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  rowLabel: { fontSize: '12px', color: 'var(--text-primary)', fontWeight: '600' },
  rowBadge: {
    border: '1px solid currentColor',
    borderRadius: '4px',
    padding: '1px 8px',
    fontSize: '10px',
    fontWeight: '700',
    letterSpacing: '0.03em',
  },
  basis: { margin: '6px 0 0 0', fontSize: '11px', lineHeight: 1.5, color: 'var(--text-secondary)', fontStyle: 'italic' },
  finalVerdict: { display: 'flex', alignItems: 'center', gap: '10px', marginTop: '2px' },
  finalLabel: { fontSize: '12px', color: 'var(--text-primary)', fontWeight: '600' },
  finalBadge: {
    padding: '3px 10px',
    borderRadius: '4px',
    color: 'var(--bg)',
    fontSize: '11px',
    fontWeight: 700,
    letterSpacing: '0.03em',
  },
};

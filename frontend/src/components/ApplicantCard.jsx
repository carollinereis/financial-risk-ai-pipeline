// src/components/ApplicantCard.jsx
const DECISION_COLORS = {
  APPROVED: 'var(--status-approved)',
  REJECTED: 'var(--status-rejected)',
  'MANUAL REVIEW REQUIRED': 'var(--status-review)',
};

// The same fields the profile drawer shows, plus the verdict badge and the
// audit trigger - the drawer stays the place for the full transcript, this is
// the at-a-glance summary the customer view opens on.
export function ApplicantCard({ profile, error, audit, onOpenReport, onClear }) {
  if (error) {
    return (
      <div style={cardStyles.card}>
        <div style={cardStyles.errorBox}>Failed to load applicant profile: {error}</div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div style={cardStyles.card}>
        <div style={cardStyles.loading}>Loading applicant…</div>
      </div>
    );
  }

  const { audit: report, loadingSaved, loading, taskStatus, auditError, justCompleted, runAudit } = audit;
  const decision = report?.decision;

  return (
    <div style={cardStyles.card}>
      <div style={cardStyles.head}>
        <div>
          <h2 style={cardStyles.name}>{profile.full_name}</h2>
          <span style={cardStyles.meta}>
            #{profile.customer_id} · CPF {profile.cpf} · {profile.email} · {profile.phone_number}
          </span>
        </div>
        <div style={cardStyles.headActions}>
          {loadingSaved ? (
            <span style={{ ...cardStyles.badge, ...cardStyles.badgeMuted }}>Checking…</span>
          ) : decision ? (
            <span
              style={{ ...cardStyles.badge, background: DECISION_COLORS[decision] || 'var(--text-secondary)' }}
            >
              {decision}
            </span>
          ) : (
            <span style={{ ...cardStyles.badge, ...cardStyles.badgeMuted }}>Not analyzed</span>
          )}
          {onClear && (
            <button type="button" style={cardStyles.backBtn} onClick={onClear}>
              ← Back to portfolio
            </button>
          )}
        </div>
      </div>

      <div style={cardStyles.grid}>
        <Field label="Requested Loan" value={`$${profile.loan_amount_requested?.toLocaleString()}`} />
        <Field label="Annual Income" value={`$${profile.annual_income?.toLocaleString()}`} />
        <Field label="Credit Score" value={profile.credit_score} />
        <Field label="DTI Ratio" value={`${(profile.debt_to_income_ratio * 100).toFixed(1)}%`} />
        <Field
          label="ML Default Probability"
          value={`${(profile.live_xgb_risk_score * 100).toFixed(2)}%`}
          valueColor={profile.live_xgb_risk_score > 0.5 ? 'var(--status-rejected)' : 'var(--status-approved)'}
        />
        <Field label="Delinquencies (2yr)" value={profile.delinquencies_2yrs} />
      </div>

      {justCompleted && !auditError && (
        <div style={cardStyles.confirmation}>Audit complete: {justCompleted}</div>
      )}

      {auditError && (
        <div style={cardStyles.banner}>
          <strong>Audit failed.</strong> {auditError}
        </div>
      )}

      <div style={cardStyles.actions}>
        <button type="button" onClick={runAudit} disabled={loading} style={cardStyles.auditBtn}>
          {loading
            ? taskStatus === 'PROCESSING'
              ? 'Running audit…'
              : 'Queued…'
            : auditError
              ? 'Try again'
              : report
                ? 'Re-run committee audit'
                : 'Run committee audit'}
        </button>
        <button type="button" onClick={onOpenReport} style={cardStyles.reportBtn}>
          Open full report
        </button>
      </div>
    </div>
  );
}

function Field({ label, value, valueColor }) {
  return (
    <div>
      <span style={cardStyles.fieldLabel}>{label}</span>
      <div style={{ ...cardStyles.fieldValue, color: valueColor || 'var(--text-primary)' }}>{value}</div>
    </div>
  );
}

const cardStyles = {
  card: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    padding: '20px',
  },
  loading: { color: 'var(--text-secondary)', fontSize: '13px' },
  errorBox: { color: 'var(--status-rejected)', fontSize: '13px' },
  head: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    flexWrap: 'wrap',
    gap: '12px',
    marginBottom: '16px',
    paddingBottom: '14px',
    borderBottom: '1px solid var(--border)',
  },
  name: { margin: 0, fontSize: '18px', color: 'var(--text-primary)' },
  meta: { fontSize: '12px', color: 'var(--text-secondary)' },
  headActions: { display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' },
  badge: {
    padding: '4px 10px',
    borderRadius: '4px',
    color: 'var(--bg)',
    fontSize: '11px',
    fontWeight: 700,
    letterSpacing: '0.03em',
    whiteSpace: 'nowrap',
  },
  badgeMuted: { background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-secondary)' },
  backBtn: {
    background: 'transparent',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border)',
    borderRadius: '6px',
    padding: '6px 12px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
    gap: '14px',
    marginBottom: '16px',
  },
  fieldLabel: { display: 'block', fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '2px' },
  fieldValue: { fontSize: '15px', fontWeight: '700' },
  // Neutral accent, not a status color: this confirms the run finished, not
  // that the verdict is good news - a REJECTED outcome would misread as
  // positive framing if this reused the green "approved" status color.
  confirmation: {
    background: 'var(--bg)',
    border: '1px solid var(--accent)',
    borderRadius: '6px',
    padding: '10px 12px',
    fontSize: '12px',
    fontWeight: '600',
    color: 'var(--accent)',
    marginBottom: '12px',
  },
  banner: {
    background: 'var(--bg)',
    border: '1px solid var(--status-rejected)',
    borderRadius: '6px',
    padding: '10px 12px',
    fontSize: '12px',
    color: 'var(--status-rejected)',
    marginBottom: '12px',
  },
  actions: { display: 'flex', gap: '10px', flexWrap: 'wrap' },
  auditBtn: {
    background: 'var(--accent)',
    color: 'var(--bg)',
    border: 'none',
    borderRadius: '6px',
    padding: '10px 16px',
    fontSize: '12px',
    fontWeight: '700',
    cursor: 'pointer',
  },
  reportBtn: {
    background: 'transparent',
    color: 'var(--accent)',
    border: '1px solid var(--accent)',
    borderRadius: '6px',
    padding: '10px 16px',
    fontSize: '12px',
    fontWeight: '700',
    cursor: 'pointer',
  },
};

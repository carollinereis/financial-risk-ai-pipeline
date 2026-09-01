// src/components/CustomerDrawer.jsx
import { useState, useEffect } from 'react';
import { API_BASE } from '../config';
import { AgentReport } from './AgentReport';

const DECISION_COLORS = {
  APPROVED: 'var(--status-approved)',
  REJECTED: 'var(--status-rejected)',
  'MANUAL REVIEW REQUIRED': 'var(--status-review)',
};

// The committee's own prose repeats its policy list verbatim for every applicant.
// Only the rationale is applicant-specific, so that is what the summary shows.
const extractRationale = (text) => {
  const match = (text || '').match(/EXECUTIVE RATIONALE\s*:?\s*\**\s*([\s\S]+)/i);
  return (match ? match[1] : text || '').trim();
};

const formatDate = (value) => {
  if (!value) return null;
  const parsed = new Date(value.replace(' ', 'T'));
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
};

const daysSince = (value) => {
  if (!value) return null;
  const parsed = new Date(value.replace(' ', 'T'));
  if (Number.isNaN(parsed.getTime())) return null;
  return Math.floor((Date.now() - parsed.getTime()) / 86_400_000);
};

// A report older than this is flagged for a look, not invalidated: the committee's
// reasoning may still hold, but nobody should assume it does without checking.
const STALE_AFTER_DAYS = 14;
// Below this the two probabilities are the same score with rounding noise between
// them; the saved value is persisted to two decimals as a percentage.
const DRIFT_EPSILON = 0.005;

export function CustomerDrawer({ customerId, onClose, onAuditComplete }) {
  const [profile, setProfile] = useState(null);
  const [audit, setAudit] = useState(null);
  // Distinguishes a replayed transcript from one produced by the run just made,
  // so the header can state which the underwriter is reading.
  const [auditSource, setAuditSource] = useState(null);
  const [loadingSaved, setLoadingSaved] = useState(true);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!customerId) return;

    const controller = new AbortController();
    fetch(`${API_BASE}/customers/${customerId}`, { signal: controller.signal })
      .then(res => {
        if (!res.ok) throw new Error(`GET /customers/${customerId} -> ${res.status}`);
        return res.json();
      })
      .then(data => setProfile(data))
      .catch(err => {
        if (err.name !== 'AbortError') console.error("Failed to load customer profile:", err);
      });

    // The saved transcript is a plain DuckDB read: opening a file never spends an
    // LLM call, so the committee's last verdict is on screen immediately. A 404
    // simply means this client has not been through the committee yet.
    fetch(`${API_BASE}/customers/${customerId}/audit`, { signal: controller.signal })
      .then(res => {
        if (res.status === 404) return null;
        if (!res.ok) throw new Error(`GET /customers/${customerId}/audit -> ${res.status}`);
        return res.json();
      })
      .then(data => {
        if (data) {
          setAudit(data);
          setAuditSource('saved');
        }
        setLoadingSaved(false);
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error("Failed to load saved audit:", err);
          setLoadingSaved(false);
        }
      });

    // Switching clients fast must not let a slow earlier response overwrite a newer one.
    return () => controller.abort();
  }, [customerId]);

  const runAudit = () => {
    setLoading(true);
    fetch(`${API_BASE}/customers/${customerId}/audit`, { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        setAudit(data);
        setAuditSource('fresh');
        setLoading(false);
        // An audit writes decision_status, so the aggregate views are now stale.
        onAuditComplete?.();
      })
      .catch(err => {
        console.error("Audit error:", err);
        setLoading(false);
      });
  };

  const lastAnalyzed = formatDate(audit?.last_analyzed_at);
  const auditAgeDays = daysSince(audit?.last_analyzed_at);
  const isStale = auditSource === 'saved' && auditAgeDays !== null && auditAgeDays >= STALE_AFTER_DAYS;

  // The committee reasoned from the model score as it stood at audit time. If the
  // model has re-scored the client since, the report argues from a number that no
  // longer holds — the one thing that decides whether it can be trusted as-is.
  const savedScore = auditSource === 'saved' ? audit?.xgb_risk_score : null;
  const liveScore = profile?.live_xgb_risk_score;
  const hasDrift =
    savedScore != null &&
    liveScore != null &&
    Math.abs(liveScore - savedScore) > DRIFT_EPSILON;

  if (!customerId || !profile) return null;

  return (
    <div style={drawerStyles.overlay} onClick={onClose}>
      <div style={drawerStyles.panel} onClick={e => e.stopPropagation()}>
        <div style={drawerStyles.header}>
          <h2>Customer Profile #{profile.customer_id}</h2>
          <button onClick={onClose} style={drawerStyles.closeBtn}>✕</button>
        </div>

        <div style={drawerStyles.body}>
          {/* Section 1: Customer Info */}
          <div style={drawerStyles.section}>
            <h3 style={{ color: 'var(--accent)', marginBottom: '10px' }}>Personal & Financial Demographics</h3>
            <div style={drawerStyles.grid}>
              <div><span style={drawerStyles.label}>Full Name:</span> <strong>{profile.full_name}</strong></div>
              <div><span style={drawerStyles.label}>CPF (Masked):</span> <strong>{profile.cpf}</strong></div>
              <div><span style={drawerStyles.label}>Credit Score:</span> <strong>{profile.credit_score}</strong></div>
              <div><span style={drawerStyles.label}>DTI Ratio:</span> <strong>{(profile.debt_to_income_ratio * 100).toFixed(1)}%</strong></div>
              <div><span style={drawerStyles.label}>Annual Income:</span> <strong>${profile.annual_income?.toLocaleString()}</strong></div>
              <div><span style={drawerStyles.label}>Requested Loan:</span> <strong>${profile.loan_amount_requested?.toLocaleString()}</strong></div>
            </div>
          </div>

          {/* Section 2: Machine Learning Score */}
          <div style={drawerStyles.section}>
            <h3 style={{ color: 'var(--accent)', marginBottom: '10px' }}>ML Default Probability</h3>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: profile.live_xgb_risk_score > 0.5 ? 'var(--status-rejected)' : 'var(--status-approved)' }}>
              {(profile.live_xgb_risk_score * 100).toFixed(2)}%
            </div>
          </div>

          {/* Section 3: Notes */}
          <div style={drawerStyles.section}>
            <h3 style={{ color: 'var(--accent)', marginBottom: '6px' }}>Sanitized Underwriter Notes</h3>
            <p style={{ fontStyle: 'italic', fontSize: '13px', color: 'var(--text-secondary)' }}>
              {profile.sanitized_notes || "No historical notes recorded."}
            </p>
          </div>

          {/* Section 4: Live Llama 3 Multi-Agent Audit Trigger */}
          <div style={drawerStyles.section}>
            <div style={drawerStyles.auditHead}>
              <h3 style={{ color: 'var(--accent)', margin: 0 }}>Multi-Agent Committee Report</h3>
              {audit && auditSource === 'saved' && (
                <span style={drawerStyles.savedTag}>
                  Saved report{lastAnalyzed ? ` · ${lastAnalyzed}` : ''}
                </span>
              )}
              {audit && auditSource === 'fresh' && (
                <span style={drawerStyles.savedTag}>Fresh committee run</span>
              )}
            </div>

            {/* The saved report is the default view; a fresh run is an explicit,
                separately-labelled action because it costs three LLM calls. */}
            {!audit && !loadingSaved && (
              <p style={drawerStyles.noAudit}>
                No committee audit has been recorded for this client yet.
              </p>
            )}

            <button
              onClick={runAudit}
              disabled={loading}
              style={audit ? drawerStyles.rerunBtn : drawerStyles.auditBtn}
            >
              {loading
                ? "Running Multi-Agent Audit..."
                : audit
                  ? "Re-run Multi-Agent Audit"
                  : "Run Executive AI Audit"}
            </button>

            {hasDrift && (
              <div style={{ ...drawerStyles.banner, borderColor: 'var(--status-review)' }}>
                <strong>Model has re-scored this client since the audit.</strong> The committee
                reasoned from {(savedScore * 100).toFixed(2)}%; the model now reports{' '}
                {(liveScore * 100).toFixed(2)}%. Re-run before relying on this verdict.
              </div>
            )}

            {isStale && !hasDrift && (
              <div style={{ ...drawerStyles.banner, borderColor: 'var(--border)' }}>
                This report is {auditAgeDays} days old. The model score is unchanged, but the
                underwriter notes it cites may not be.
              </div>
            )}

            {audit?.human_overridden && (
              <div style={{ ...drawerStyles.banner, borderColor: 'var(--accent)' }}>
                <strong>Underwriter override on record.</strong>
                <div style={drawerStyles.overrideMeta}>
                  {audit.overridden_by || 'Unattributed'} ·{' '}
                  {formatDate(audit.overridden_at) || 'date unknown'} · final status{' '}
                  {audit.decision}
                </div>
                {audit.override_notes && (
                  <p style={drawerStyles.overrideNotes}>“{audit.override_notes}”</p>
                )}
              </div>
            )}

            {audit && (
              <div style={drawerStyles.verdict}>
                <div style={drawerStyles.verdictHead}>
                  <span
                    style={{
                      ...drawerStyles.decisionBadge,
                      background: DECISION_COLORS[audit.decision] || 'var(--text-secondary)',
                    }}
                  >
                    {audit.decision}
                  </span>
                  {audit.risk_tier && (
                    <span style={drawerStyles.tier}>Risk tier: {audit.risk_tier}</span>
                  )}
                  {audit.execution_time_ms > 0 && (
                    <span style={drawerStyles.tier}>
                      Committee runtime: {(audit.execution_time_ms / 1000).toFixed(1)}s
                    </span>
                  )}
                </div>

                <AgentReport text={extractRationale(audit.cro_decision || audit.cro_report)} />

                {/* Full transcripts stay available for the audit trail, collapsed so
                    the drawer opens on the part an underwriter actually skims. */}
                <details style={drawerStyles.details}>
                  <summary style={drawerStyles.summary}>Full committee transcript</summary>
                  <div style={drawerStyles.transcript}>
                    <AgentSection
                      label="Quantitative Agent"
                      verdict={audit.quant_verdict}
                      basis={audit.quant_basis}
                      text={audit.quant_analysis}
                    />
                    <AgentSection
                      label="Qualitative Agent"
                      verdict={audit.qual_verdict}
                      basis={audit.qual_basis}
                      text={audit.qual_analysis}
                    />
                    <AgentSection
                      label="CRO Decision Agent"
                      verdict={audit.cro_verdict}
                      basis={audit.cro_basis}
                      text={audit.cro_decision || audit.cro_report}
                    />
                  </div>
                </details>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// An agent's recorded vote can differ from the conclusion in its own prose, because
// deterministic policy may have overruled it. The basis line carries that reasoning,
// so the transcript never shows a verdict the report appears to contradict.
function AgentSection({ label, verdict, basis, text }) {
  return (
    <div>
      <h5 style={drawerStyles.transcriptLabel}>
        {label}
        {verdict && <span style={drawerStyles.transcriptVerdict}>{verdict}</span>}
      </h5>
      {basis && <p style={drawerStyles.transcriptBasis}>{basis}</p>}
      <AgentReport text={text} />
    </div>
  );
}

const drawerStyles = {
  overlay: { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', justifyContent: 'flex-end', zIndex: 1000 },
  // Wide enough for a comfortable reading measure on the agent prose, capped so it
  // never swallows the dashboard behind it on a narrow screen.
  panel: { width: 'min(560px, 100vw)', height: '100%', background: 'var(--surface)', borderLeft: '1px solid var(--border)', padding: '24px', overflowY: 'auto' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid var(--border)', paddingBottom: '10px' },
  closeBtn: { background: 'none', border: 'none', color: 'var(--text-primary)', fontSize: '18px', cursor: 'pointer' },
  body: { display: 'flex', flexDirection: 'column', gap: '20px' },
  section: { background: 'var(--surface-hover)', padding: '15px', borderRadius: '8px', border: '1px solid var(--border)' },
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '13px' },
  label: { color: 'var(--text-secondary)', display: 'block', fontSize: '11px' },
  auditBtn: { width: '100%', padding: '12px', background: 'var(--accent)', color: 'var(--bg)', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' },
  // Secondary weight once a saved report exists: re-running is the exception, not the default path.
  rerunBtn: { width: '100%', padding: '10px', background: 'transparent', color: 'var(--accent)', border: '1px solid var(--accent)', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer', fontSize: '12px' },
  auditHead: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', flexWrap: 'wrap', marginBottom: '10px' },
  savedTag: { fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' },
  banner: { background: 'var(--bg)', border: '1px solid', borderRadius: '6px', padding: '10px 12px', fontSize: '12px', color: 'var(--text-primary)', lineHeight: 1.5, marginBottom: '10px' },
  overrideMeta: { fontSize: '11px', color: 'var(--text-secondary)', marginTop: '3px' },
  overrideNotes: { fontSize: '12px', fontStyle: 'italic', color: 'var(--text-primary)', margin: '6px 0 0 0' },
  noAudit: { fontSize: '12px', color: 'var(--text-secondary)', margin: '0 0 10px 0' },
  verdict: { marginTop: '15px', background: 'var(--bg)', padding: '15px', borderRadius: '8px', border: '1px solid var(--border)' },
  verdictHead: { display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px', flexWrap: 'wrap' },
  decisionBadge: { padding: '4px 10px', borderRadius: '4px', color: 'var(--bg)', fontSize: '11px', fontWeight: 700, letterSpacing: '0.03em' },
  tier: { fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase' },
  details: { marginTop: '14px', borderTop: '1px solid var(--border)', paddingTop: '10px' },
  summary: { cursor: 'pointer', fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' },
  transcript: { marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '6px' },
  transcriptLabel: { margin: '10px 0 0 0', fontSize: '11px', color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'flex', alignItems: 'center', gap: '8px' },
  transcriptVerdict: { border: '1px solid var(--border)', borderRadius: '4px', padding: '1px 6px', fontSize: '10px', color: 'var(--text-secondary)', letterSpacing: '0.02em' },
  transcriptBasis: { margin: '4px 0 6px 0', fontSize: '11px', lineHeight: 1.5, color: 'var(--text-secondary)', fontStyle: 'italic' }
};
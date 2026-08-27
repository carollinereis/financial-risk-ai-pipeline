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

export function CustomerDrawer({ customerId, onClose, onAuditComplete }) {
  const [profile, setProfile] = useState(null);
  const [audit, setAudit] = useState(null);
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

    // Switching clients fast must not let a slow earlier response overwrite a newer one.
    return () => controller.abort();
  }, [customerId]);

  const runAudit = () => {
    setLoading(true);
    fetch(`${API_BASE}/customers/${customerId}/audit`, { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        setAudit(data);
        setLoading(false);
        // An audit writes decision_status, so the aggregate views are now stale.
        onAuditComplete?.();
      })
      .catch(err => {
        console.error("Audit error:", err);
        setLoading(false);
      });
  };

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
            <button onClick={runAudit} disabled={loading} style={drawerStyles.auditBtn}>
              {loading ? "Running Multi-Agent Audit..." : "Run Executive AI Audit"}
            </button>

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
                  <span style={drawerStyles.tier}>Risk tier: {audit.risk_tier}</span>
                </div>

                <AgentReport text={extractRationale(audit.cro_decision || audit.cro_report)} />

                {/* Full transcripts stay available for the audit trail, collapsed so
                    the drawer opens on the part an underwriter actually skims. */}
                <details style={drawerStyles.details}>
                  <summary style={drawerStyles.summary}>Full committee transcript</summary>
                  <div style={drawerStyles.transcript}>
                    <h5 style={drawerStyles.transcriptLabel}>Quantitative Agent</h5>
                    <AgentReport text={audit.quant_analysis} />
                    <h5 style={drawerStyles.transcriptLabel}>Qualitative Agent</h5>
                    <AgentReport text={audit.qual_analysis} />
                    <h5 style={drawerStyles.transcriptLabel}>CRO Decision Agent</h5>
                    <AgentReport text={audit.cro_decision || audit.cro_report} />
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
  verdict: { marginTop: '15px', background: 'var(--bg)', padding: '15px', borderRadius: '8px', border: '1px solid var(--border)' },
  verdictHead: { display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px', flexWrap: 'wrap' },
  decisionBadge: { padding: '4px 10px', borderRadius: '4px', color: 'var(--bg)', fontSize: '11px', fontWeight: 700, letterSpacing: '0.03em' },
  tier: { fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase' },
  details: { marginTop: '14px', borderTop: '1px solid var(--border)', paddingTop: '10px' },
  summary: { cursor: 'pointer', fontSize: '11px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' },
  transcript: { marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '6px' },
  transcriptLabel: { margin: '10px 0 0 0', fontSize: '11px', color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.04em' }
};
// src/components/PolicyReference.jsx
import { useEffect, useState } from 'react';
import { API_BASE } from '../config';

// Rendered from the same src/domain/policy definitions the CRO agent is given, so a
// rule shown here is guaranteed to be the rule the committee was judged against.
export function PolicyReference() {
  const [open, setOpen] = useState(false);
  const [reference, setReference] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open || reference) return;

    const controller = new AbortController();
    fetch(`${API_BASE}/api/dashboard/policy-reference`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`GET /api/dashboard/policy-reference -> ${res.status}`);
        return res.json();
      })
      .then(setReference)
      .catch((err) => {
        if (err.name !== 'AbortError') setError(err.message);
      });

    return () => controller.abort();
  }, [open, reference]);

  // Escape closes, matching the drawer's dismiss behaviour.
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const t = reference?.thresholds;

  return (
    <>
      <button type="button" style={styles.trigger} onClick={() => setOpen(true)}>
        <span style={styles.triggerIcon} aria-hidden="true">§</span>
        <span>
          <span style={styles.triggerTitle}>Underwriting Policy</span>
          <span style={styles.triggerHint}>
            Thresholds and committee rules
          </span>
        </span>
      </button>

      {open && (
        <div style={styles.overlay} onClick={() => setOpen(false)}>
          <div
            style={styles.modal}
            role="dialog"
            aria-modal="true"
            aria-label="Underwriting policy reference"
            onClick={(e) => e.stopPropagation()}
          >
            <div style={styles.header}>
              <h2 style={styles.title}>Underwriting Policy Reference</h2>
              <button type="button" onClick={() => setOpen(false)} style={styles.close}>
                ✕
              </button>
            </div>

            {error ? (
              <div style={styles.error}>Failed to load policy reference: {error}</div>
            ) : !reference ? (
              <div style={styles.loading}>Loading policy reference...</div>
            ) : (
              <>
                <div style={styles.thresholds}>
                  <Threshold label="Minimum credit score" value={t.min_credit_score} />
                  <Threshold label="Maximum DTI" value={`${(t.max_dti * 100).toFixed(0)}%`} />
                  <Threshold
                    label="XGBoost high-risk gate"
                    value={`${(t.xgb_high_risk_threshold * 100).toFixed(0)}%`}
                  />
                  <Threshold label="Subprime score (Policy 3)" value={t.subprime_credit_score} />
                </div>

                <p style={styles.note}>
                  Quantitative standing is computed in code before the committee runs — the
                  agents cannot alter it. Any one threshold breach on its own yields CRITICAL
                  RISK.
                </p>

                <ol style={styles.list}>
                  {reference.policies.map((policy) => (
                    <li key={policy.id} style={styles.item}>
                      <div style={styles.itemTitle}>
                        Policy {policy.id} — {policy.title}
                      </div>
                      <div style={styles.rule}>{policy.rule}</div>
                      <div style={styles.detail}>{policy.detail}</div>
                    </li>
                  ))}
                </ol>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}

function Threshold({ label, value }) {
  return (
    <div style={styles.threshold}>
      <div style={styles.thresholdLabel}>{label}</div>
      <div style={styles.thresholdValue}>{value}</div>
    </div>
  );
}

const styles = {
  trigger: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    width: '100%',
    textAlign: 'left',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    padding: '14px 18px',
    marginBottom: '24px',
    cursor: 'pointer',
    color: 'var(--text-primary)',
    fontFamily: 'inherit',
  },
  triggerIcon: {
    fontSize: '20px',
    color: 'var(--accent)',
    fontWeight: 700,
    lineHeight: 1,
  },
  triggerTitle: { display: 'block', fontSize: '13px', fontWeight: 600 },
  triggerHint: { display: 'block', fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' },
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1100,
    padding: '24px',
  },
  modal: {
    width: 'min(680px, 100%)',
    maxHeight: '85vh',
    overflowY: 'auto',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    padding: '24px',
  },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' },
  title: { margin: 0, fontSize: '16px', color: 'var(--text-primary)' },
  close: { background: 'none', border: 'none', color: 'var(--text-primary)', fontSize: '18px', cursor: 'pointer' },
  thresholds: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px' },
  threshold: { background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '8px', padding: '10px 12px' },
  thresholdLabel: { fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' },
  thresholdValue: { fontSize: '18px', fontWeight: 700, color: 'var(--accent)', marginTop: '4px' },
  note: { fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.6, margin: '14px 0 4px 0' },
  list: { listStyle: 'none', padding: 0, margin: '10px 0 0 0', display: 'flex', flexDirection: 'column', gap: '14px' },
  item: { borderTop: '1px solid var(--border)', paddingTop: '12px' },
  itemTitle: { fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' },
  rule: { fontSize: '12.5px', color: 'var(--text-primary)', lineHeight: 1.55 },
  detail: { fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.55, marginTop: '5px' },
  loading: { fontSize: '13px', color: 'var(--text-secondary)', padding: '16px 0' },
  error: { fontSize: '13px', color: 'var(--status-rejected)', padding: '16px 0' },
};

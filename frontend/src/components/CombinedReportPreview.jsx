// src/components/CombinedReportPreview.jsx
import { useRef, useState } from 'react';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import { DECISION_COLORS, drawerStyles } from './CustomerDrawer';

// Combines data already loaded into the drawer's own state (profile, audit,
// extraction) into one printable view. No separate fetch: CustomerDrawer only
// renders this once both halves exist, so there is never a partial report here.
export function CombinedReportPreview({ profile, audit, extraction, onClose }) {
  const contentRef = useRef(null);
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      // html2canvas rasterizes the DOM, so the PDF is an image of exactly what
      // is on screen right now - not selectable text. Accepted v1 trade-off: it
      // guarantees the download matches the reviewed preview with no separate
      // PDF layout to keep in sync, at the cost of text search/copy in the PDF.
      const canvas = await html2canvas(contentRef.current, { scale: 2 });
      const imageData = canvas.toDataURL('image/png');
      const pdf = new jsPDF({
        orientation: canvas.width >= canvas.height ? 'landscape' : 'portrait',
        unit: 'px',
        format: [canvas.width, canvas.height],
      });
      pdf.addImage(imageData, 'PNG', 0, 0, canvas.width, canvas.height);
      pdf.save(`customer-${profile.customer_id}-report.pdf`);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div
      style={styles.overlay}
      onClick={(e) => {
        e.stopPropagation();
        onClose();
      }}
    >
      <div style={styles.panel} onClick={(e) => e.stopPropagation()}>
        <div style={drawerStyles.header}>
          <h2>Combined Report Preview</h2>
          <div style={styles.actions}>
            <button onClick={handleDownload} disabled={downloading} style={drawerStyles.auditBtn}>
              {downloading ? 'Preparing PDF...' : 'Download PDF'}
            </button>
            <button onClick={onClose} style={drawerStyles.closeBtn}>✕</button>
          </div>
        </div>

        <div ref={contentRef} style={styles.content}>
          <h2 style={styles.title}>Customer Risk Report</h2>
          <p style={styles.subtitle}>Customer #{profile.customer_id} &middot; {profile.full_name}</p>

          <section style={drawerStyles.section}>
            <h3 style={{ color: 'var(--accent)', marginBottom: '10px' }}>
              Personal & Financial Demographics
            </h3>
            <div style={drawerStyles.grid}>
              <div><span style={drawerStyles.label}>Full Name:</span> <strong>{profile.full_name}</strong></div>
              <div><span style={drawerStyles.label}>Credit Score:</span> <strong>{profile.credit_score}</strong></div>
              <div><span style={drawerStyles.label}>DTI Ratio:</span> <strong>{(profile.debt_to_income_ratio * 100).toFixed(1)}%</strong></div>
              <div><span style={drawerStyles.label}>Annual Income:</span> <strong>${profile.annual_income?.toLocaleString()}</strong></div>
              <div><span style={drawerStyles.label}>Requested Loan:</span> <strong>${profile.loan_amount_requested?.toLocaleString()}</strong></div>
              <div><span style={drawerStyles.label}>ML Default Probability:</span> <strong>{(profile.live_xgb_risk_score * 100).toFixed(2)}%</strong></div>
            </div>
          </section>

          <section style={drawerStyles.section}>
            <h3 style={{ color: 'var(--accent)', marginBottom: '10px' }}>Committee Decision</h3>
            <div style={drawerStyles.verdictHead}>
              <span
                style={{
                  ...drawerStyles.decisionBadge,
                  background: DECISION_COLORS[audit.decision] || 'var(--text-secondary)',
                }}
              >
                {audit.decision}
              </span>
              {audit.risk_tier && <span style={drawerStyles.tier}>Risk tier: {audit.risk_tier}</span>}
            </div>
            <p style={styles.paragraph}>{audit.rationale}</p>
          </section>

          <p style={styles.scopeLine}>
            Document Intelligence checks the contract's paperwork only (rate, signature,
            borrower match) — it does not evaluate credit risk, which is the Committee
            Decision's job above.
          </p>

          <section style={drawerStyles.section}>
            <h3 style={{ color: 'var(--accent)', marginBottom: '10px' }}>Document Intelligence</h3>
            <div style={drawerStyles.grid}>
              <div><span style={drawerStyles.label}>Borrower Name:</span> <strong>{extraction.entities.borrower_name || 'Not found'}</strong></div>
              <div>
                <span style={drawerStyles.label}>Loan Amount:</span>{' '}
                <strong>
                  {extraction.entities.loan_amount != null
                    ? `R$ ${extraction.entities.loan_amount.toLocaleString()}`
                    : 'Not found'}
                </strong>
              </div>
              <div>
                <span style={drawerStyles.label}>Interest Rate:</span>{' '}
                <strong>
                  {extraction.entities.interest_rate != null
                    ? `${extraction.entities.interest_rate}%`
                    : 'Not found'}
                </strong>
              </div>
              <div>
                <span style={drawerStyles.label}>Term:</span>{' '}
                <strong>
                  {extraction.entities.term_months != null
                    ? `${extraction.entities.term_months} months`
                    : 'Not found'}
                </strong>
              </div>
              <div>
                <span style={drawerStyles.label}>Signature:</span>{' '}
                <strong>{extraction.entities.signature_present ? 'Present' : 'Missing'}</strong>
              </div>
            </div>

            <div style={styles.block}>
              <span style={drawerStyles.label}>Document Issues:</span>
              {extraction.risk_flags.length === 0 ? (
                <p style={styles.paragraph}>None found.</p>
              ) : (
                <ul style={styles.flagList}>
                  {extraction.risk_flags.map((flag, i) => (
                    <li key={i}>{flag}</li>
                  ))}
                </ul>
              )}
            </div>

            <div style={styles.block}>
              <span style={drawerStyles.label}>Executive Summary:</span>
              <p style={styles.paragraph}>{extraction.executive_summary}</p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0,0,0,0.6)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1100,
    padding: '24px',
  },
  panel: {
    width: 'min(640px, 100%)',
    maxHeight: '90vh',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '8px',
    padding: '24px',
    overflowY: 'auto',
  },
  actions: { display: 'flex', alignItems: 'center', gap: '12px' },
  content: { display: 'flex', flexDirection: 'column', gap: '16px', background: 'var(--surface)' },
  title: { margin: 0 },
  subtitle: { margin: '4px 0 0 0', color: 'var(--text-secondary)', fontSize: '13px' },
  paragraph: { fontSize: '13px', lineHeight: 1.6, color: 'var(--text-primary)', margin: '6px 0 0 0' },
  scopeLine: { fontSize: '11px', color: 'var(--text-secondary)', fontStyle: 'italic', margin: 0, textAlign: 'center' },
  block: { marginTop: '10px' },
  flagList: { margin: '4px 0 0 0', paddingLeft: '18px', fontSize: '12px', lineHeight: 1.6 },
};

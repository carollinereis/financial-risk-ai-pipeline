// src/components/DocumentIntelligence.jsx
import { drawerStyles } from './CustomerDrawer';

// Presentational: the underlying useDocumentExtraction() call lives in
// CustomerDrawer, not here, so its extraction result can also gate the
// "View Report" action there without a second, duplicate hook instance polling
// the same task in parallel.
export function DocumentIntelligence({ extraction, loading, taskStatus, error, runExtraction }) {
  return (
    <div style={drawerStyles.section}>
      <h3 style={{ color: 'var(--accent)', marginBottom: '10px' }}>Document Intelligence</h3>
      <p style={drawerStyles.noAudit}>
        Extracts key entities and risk flags from this customer's own mock loan
        contract. A single extraction call, independent of the committee audit above.
      </p>

      <button onClick={runExtraction} disabled={loading} style={drawerStyles.auditBtn}>
        {loading
          ? taskStatus === 'PROCESSING'
            ? 'Extracting...'
            : 'Queued...'
          : extraction
            ? 'Re-run Extraction'
            : 'Extract Document'}
      </button>

      {error && (
        <div style={{ ...drawerStyles.banner, borderColor: 'var(--status-rejected)' }}>
          <strong>Extraction error.</strong> {error}
        </div>
      )}

      {extraction?.review_status === 'NEEDS_REVIEW' && (
        <div style={{ ...drawerStyles.banner, borderColor: 'var(--status-review)' }}>
          The model's response didn't fully parse; fields below that could not be
          validated are shown as not found rather than guessed.
        </div>
      )}

      {extraction && (
        <div style={drawerStyles.verdict}>
          <div style={drawerStyles.grid}>
            <div>
              <span style={drawerStyles.label}>Borrower Name:</span>{' '}
              <strong>{extraction.entities.borrower_name || 'Not found'}</strong>
            </div>
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
              <strong
                style={{
                  color: extraction.entities.signature_present
                    ? 'var(--status-approved)'
                    : 'var(--status-rejected)',
                }}
              >
                {extraction.entities.signature_present ? 'Present' : 'Missing'}
              </strong>
            </div>
          </div>

          <div style={styles.block}>
            <span style={drawerStyles.label}>Document Issues:</span>
            {extraction.risk_flags.length === 0 ? (
              <p style={{ ...drawerStyles.noAudit, color: 'var(--status-approved)', margin: '4px 0 0 0' }}>
                None found.
              </p>
            ) : (
              <ul style={styles.flagList}>
                {extraction.risk_flags.map((flag, i) => (
                  <li key={i} style={{ ...styles.flag, color: 'var(--status-review)' }}>
                    {flag}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div style={styles.block}>
            <span style={drawerStyles.label}>Executive Summary:</span>
            <p style={styles.summary}>{extraction.executive_summary || 'No summary generated.'}</p>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  block: { marginTop: '14px' },
  flagList: { margin: '4px 0 0 0', paddingLeft: '18px' },
  flag: { fontSize: '12px', lineHeight: 1.6 },
  summary: { fontSize: '13px', lineHeight: 1.6, color: 'var(--text-primary)', margin: '4px 0 0 0' },
};

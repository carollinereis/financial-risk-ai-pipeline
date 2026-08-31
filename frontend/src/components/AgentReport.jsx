// src/components/AgentReport.jsx
// The agents emit loose markdown (Llama wraps labels as **LABEL:**, bullets as
// '-' or '*', numbered steps as '1.'). Rendering it raw in a <pre> shows the
// asterisks, so this turns the common subset into real nodes. Deliberately not a
// full markdown parser and deliberately not dangerouslySetInnerHTML: agent output
// is model-generated text that may echo unsanitized notes.

const BULLET = /^\s*[-*•]\s+/;
const NUMBERED = /^\s*(\d+)[.)]\s+/;
// A heading is a line that is entirely a bolded label, e.g. '**Policy Application:**'
const HEADING = /^\s*\*\*(.+?)\*\*:?\s*$/;

/** Splits on ** pairs and returns alternating plain/bold nodes. */
function renderInline(text, keyPrefix) {
  return text.split(/\*\*(.+?)\*\*/g).map((chunk, i) =>
    i % 2 === 1 ? <strong key={`${keyPrefix}-b${i}`}>{chunk}</strong> : chunk,
  );
}

function renderLine(line, key) {
  const heading = line.match(HEADING);
  if (heading) {
    return (
      <h5 key={key} style={styles.heading}>
        {heading[1].replace(/:$/, '')}
      </h5>
    );
  }

  const numbered = line.match(NUMBERED);
  if (numbered) {
    return (
      <div key={key} style={styles.listItem}>
        <span style={styles.marker}>{numbered[1]}.</span>
        <span>{renderInline(line.replace(NUMBERED, ''), key)}</span>
      </div>
    );
  }

  if (BULLET.test(line)) {
    return (
      <div key={key} style={styles.listItem}>
        <span style={styles.marker}>•</span>
        <span>{renderInline(line.replace(BULLET, ''), key)}</span>
      </div>
    );
  }

  return (
    <p key={key} style={styles.paragraph}>
      {renderInline(line, key)}
    </p>
  );
}

export function AgentReport({ text, style }) {
  if (!text?.trim()) {
    return <p style={styles.paragraph}>No report returned.</p>;
  }

  const lines = text.split(/\r?\n/).filter((line) => line.trim());

  return <div style={{ ...styles.container, ...style }}>{lines.map(renderLine)}</div>;
}

const styles = {
  container: {
    fontSize: '12.5px',
    lineHeight: 1.6,
    color: 'var(--text-primary)',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  heading: {
    margin: '8px 0 2px 0',
    fontSize: '11px',
    fontWeight: 700,
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    color: 'var(--text-secondary)',
  },
  paragraph: { margin: 0 },
  listItem: { display: 'flex', gap: '8px', paddingLeft: '2px' },
  marker: { color: 'var(--accent)', flexShrink: 0, minWidth: '12px' },
};

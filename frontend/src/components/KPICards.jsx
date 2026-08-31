// src/components/KPICards.jsx
import React, { useState } from 'react';

export function KPICards({ kpis, onViewAllCustomers }) {
  return (
    <div style={kpiStyles.grid}>
      <Card
        title="Total Customers"
        value={kpis.total || 0}
        subtext="Database Records"
        action={onViewAllCustomers ? { label: 'View All →', onClick: onViewAllCustomers } : null}
      />
      <Card title="Portfolio Avg Credit Score" value={kpis.avgScore || 0} subtext="Weighted Average" />
      <Card title="Portfolio Approval Rate" value={`${kpis.approvalRate || 65}%`} subtext="Automated Policy" />
      <Card 
        title="Avg Decision Time" 
        value={`${kpis.avgTime || 4.2}s`} 
        subtext="Multi-Agent Pipeline Speed" 
        highlight 
      />
    </div>
  );
}

// An `action` turns the card into a button: the whole surface is the hit target,
// so the affordance an underwriter sees (hover lift, pointer, "View All →") and
// the thing they can actually click are the same rectangle.
function Card({ title, value, subtext, highlight, action }) {
  const [hovered, setHovered] = useState(false);
  const interactive = Boolean(action);

  const cardStyle = {
    ...kpiStyles.card,
    borderColor: highlight ? 'var(--accent)' : 'var(--border)',
    ...(interactive ? kpiStyles.interactive : null),
    ...(interactive && hovered ? kpiStyles.interactiveHover : null),
  };

  const body = (
    <>
      <span style={kpiStyles.title}>{title}</span>
      <div style={kpiStyles.value}>{value}</div>
      <div style={kpiStyles.footer}>
        <span style={kpiStyles.subtext}>{subtext}</span>
        {interactive && (
          <span style={{ ...kpiStyles.actionLabel, opacity: hovered ? 1 : 0.75 }}>
            {action.label}
          </span>
        )}
      </div>
    </>
  );

  if (!interactive) {
    return <div style={cardStyle}>{body}</div>;
  }

  return (
    <button
      type="button"
      onClick={action.onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setHovered(true)}
      onBlur={() => setHovered(false)}
      style={{ ...cardStyle, textAlign: 'left', font: 'inherit' }}
    >
      {body}
    </button>
  );
}

const kpiStyles = {
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '16px',
    marginBottom: '24px',
  },
  card: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    padding: '18px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
  },
  interactive: {
    cursor: 'pointer',
    transition: 'transform 120ms ease, border-color 120ms ease, background 120ms ease',
  },
  interactiveHover: {
    borderColor: 'var(--accent)',
    background: 'var(--surface-hover)',
    transform: 'translateY(-2px)',
  },
  title: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    fontWeight: '500',
  },
  value: {
    fontSize: '24px',
    fontWeight: '700',
    color: 'var(--text-primary)',
    margin: '8px 0 4px 0',
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '8px',
  },
  subtext: {
    fontSize: '10px',
    color: 'var(--text-secondary)',
  },
  actionLabel: {
    fontSize: '10px',
    fontWeight: '700',
    color: 'var(--accent)',
    whiteSpace: 'nowrap',
    transition: 'opacity 120ms ease',
  }
};

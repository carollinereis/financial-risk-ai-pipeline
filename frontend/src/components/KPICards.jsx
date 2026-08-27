// src/components/KPICards.jsx
import React from 'react';

export function KPICards({ kpis }) {
  return (
    <div style={kpiStyles.grid}>
      <Card title="Total Customers" value={kpis.total || 0} subtext="Database Records" />
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

function Card({ title, value, subtext, highlight }) {
  return (
    <div style={{
      ...kpiStyles.card,
      borderColor: highlight ? 'var(--accent)' : 'var(--border)'
    }}>
      <span style={kpiStyles.title}>{title}</span>
      <div style={kpiStyles.value}>{value}</div>
      <span style={kpiStyles.subtext}>{subtext}</span>
    </div>
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
  subtext: {
    fontSize: '10px',
    color: 'var(--text-secondary)',
  }
};
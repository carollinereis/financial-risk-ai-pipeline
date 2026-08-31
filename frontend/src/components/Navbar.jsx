// src/components/Navbar.jsx
import React from 'react';
import { ThemeToggle } from './ThemeToggle';

export function Navbar({ customers, selectedId, onSelectCustomer }) {
  return (
    <header style={navStyles.header}>
      <div>
        <h1 style={navStyles.title}>FINANCIAL RISK AI PIPELINE</h1>
        <p style={navStyles.subtitle}>Multi-Agent Underwriting & Risk Evaluation Engine</p>
      </div>

      <div style={navStyles.actions}>
        {/* Customer Selector Dropdown */}
        <div style={navStyles.selectWrapper}>
          <label style={navStyles.label}>Select Client:</label>
          <select
            style={navStyles.select}
            value={selectedId ?? ''}
            disabled={customers.length === 0}
            onChange={(e) => onSelectCustomer(e.target.value ? Number(e.target.value) : null)}
          >
            {/* Placeholder keeps a distinct "nothing open" value, so re-picking the
                client whose drawer was just closed still fires onChange. */}
            <option value="">
              {customers.length === 0 ? 'No clients loaded' : '\u2014 Select client \u2014'}
            </option>
            {customers.map(c => (
              <option key={c.customer_id} value={c.customer_id}>
                ID {c.customer_id} - {c.full_name}
              </option>
            ))}
          </select>
        </div>

        <ThemeToggle />
      </div>
    </header>
  );
}

const navStyles = {
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingBottom: '20px',
    borderBottom: '1px solid var(--border)',
    marginBottom: '24px',
  },
  title: {
    fontSize: '20px',
    fontWeight: '700',
    color: 'var(--text-primary)',
    letterSpacing: '0.5px',
  },
  subtitle: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    marginTop: '2px',
  },
  actions: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  selectWrapper: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '8px',
    padding: '6px 12px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  label: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
  },
  select: {
    background: 'transparent',
    border: 'none',
    color: 'var(--accent)',
    fontWeight: '600',
    fontSize: '13px',
    cursor: 'pointer',
    outline: 'none',
  }
};
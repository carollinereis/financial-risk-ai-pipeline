// src/components/Navbar.jsx
import React from 'react';
import { CustomerSearch } from './CustomerSearch';
import { ThemeToggle } from './ThemeToggle';

export function Navbar({ customers, onSelectCustomer }) {
  return (
    <header style={navStyles.header}>
      <div>
        <h1 style={navStyles.title}>FINANCIAL RISK AI PIPELINE</h1>
        <p style={navStyles.subtitle}>Multi-Agent Underwriting & Risk Evaluation Engine</p>
      </div>

      <div style={navStyles.actions}>
        {/* Quick search replaces the native select: the portfolio is too long to
            scan in a dropdown, and a client's analysis status is what decides
            whether opening them costs an LLM run. */}
        <CustomerSearch customers={customers} onSelectCustomer={onSelectCustomer} />

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
};
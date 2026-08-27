// src/components/ThemeToggle.jsx
import React from 'react';
import { useTheme } from '../context/ThemeContext';

export function ThemeToggle() {
  const { theme, toggle } = useTheme();

  return (
    <button 
      onClick={toggle} 
      style={toggleStyles.button}
      aria-label="Toggle visual theme"
      title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
    >
      {theme === 'dark' ? 'Light' : 'Dark'}
    </button>
  );
}

const toggleStyles = {
  button: {
    background: 'var(--surface-hover)',
    color: 'var(--text-primary)',
    border: '1px solid var(--border)',
    borderRadius: '20px',
    padding: '6px 14px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  }
};
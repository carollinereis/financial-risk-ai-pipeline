// src/components/ThemeToggle.jsx
import React, { useState } from 'react';
import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const [hovered, setHovered] = useState(false);

  // The icon names the destination, not the current state: in dark mode the Sun
  // is the way out of it. The aria-label says the same thing in words, so the
  // button is unambiguous whether it is seen or heard.
  const isDark = theme === 'dark';
  const nextTheme = isDark ? 'light' : 'dark';
  const Icon = isDark ? Sun : Moon;

  return (
    <button
      type="button"
      onClick={toggle}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setHovered(true)}
      onBlur={() => setHovered(false)}
      style={{
        ...toggleStyles.button,
        ...(hovered ? toggleStyles.buttonHover : null),
      }}
      aria-label={`Switch to ${nextTheme} theme`}
      title={`Switch to ${nextTheme} theme`}
    >
      <Icon
        size={16}
        aria-hidden="true"
        style={{
          ...toggleStyles.icon,
          // A small rotation on hover reads as the dial it is, without animating
          // the swap itself — the icon change must stay instant to feel responsive.
          transform: hovered ? 'rotate(25deg)' : 'rotate(0deg)',
        }}
      />
    </button>
  );
}

const toggleStyles = {
  button: {
    width: '34px',
    height: '34px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--surface)',
    color: 'var(--text-secondary)',
    border: '1px solid var(--border)',
    borderRadius: '50%',
    padding: 0,
    cursor: 'pointer',
    transition: 'background 140ms ease, border-color 140ms ease, color 140ms ease',
  },
  buttonHover: {
    background: 'var(--surface-hover)',
    borderColor: 'var(--accent)',
    color: 'var(--accent)',
  },
  icon: {
    transition: 'transform 180ms ease',
  },
};

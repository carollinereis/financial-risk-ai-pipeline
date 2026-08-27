// src/hooks/useChartColors.js
import { useState, useEffect } from 'react';
import { useTheme } from '../context/ThemeContext';

export function useChartColors() {
  const { theme } = useTheme();
  const [colors, setColors] = useState({});

  useEffect(() => {
    const styles = getComputedStyle(document.documentElement);
    setColors({
      approved: styles.getPropertyValue('--status-approved').trim(),
      rejected: styles.getPropertyValue('--status-rejected').trim(),
      review: styles.getPropertyValue('--status-review').trim(),
      accent: styles.getPropertyValue('--accent').trim(),
      textPrimary: styles.getPropertyValue('--text-primary').trim(),
      textSecondary: styles.getPropertyValue('--text-secondary').trim(),
      border: styles.getPropertyValue('--border').trim(),
    });
  }, [theme]);

  return colors;
}
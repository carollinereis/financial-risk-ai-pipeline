# Skill: React Doctor

## Objective
Analyze React/Next.js code for performance bottlenecks, anti-patterns, and re-render issues.

## Checklist
1. **Re-render Optimization:** Audit `useCallback`, `useMemo`, and key props. Flag unnecessary inline function definitions in JSX loops.
2. **State Management:** Identify redundant state that can be derived from existing props or state.
3. **Effect Cleanups:** Check all `useEffect` hooks for missing dependency array items and missing cleanup returns.
4. **Component Boundary:** Verify server vs. client components (`'use client'`). Flag client components placed too high in the component tree.
# Skill: Vercel Web Guidelines

## Objective
Ensure code complies with Vercel deployment standards and Web Vitals best practices.

## Guidelines
1. **Core Web Vitals:** Ensure all images use `next/image` with explicit dimensions or fill layout. Optimize LCP and CLS.
2. **Edge & Serverless:** Keep bundle sizes low. Dynamic imports (`next/dynamic`) for heavy components.
3. **Caching & Revalidation:** Use explicit `fetch` caching options (`force-cache`, `revalidate`) or `unstable_cache`.
4. **Environment Variables:** Validate environment variables at build time using Zod schemas.
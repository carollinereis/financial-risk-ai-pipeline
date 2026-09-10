### Phase 5: Portfolio view fixes

Only change what's listed below. Do not change any data, queries, or calculations.

**1. Credit score band chart labels**
- The fourth x-axis label ("Very Good") is hidden. Force every band label to render. If this is Recharts, set `interval={0}` on the XAxis. If a label doesn't fit, wrap it onto two lines instead of hiding it.
- The top y-axis label ("38.5%") is clipped. Add top margin to the chart. Round the y-axis to clean ticks (e.g. 0–40% in steps of 10) instead of ending at the data max.

**2. Grid layout**
- The four portfolio cards use a 3-column grid, which leaves "Top 5 Largest Requested Loans" alone on the second row. Change it to a 2×2 grid on desktop, collapsing to one column on narrow screens.
- Cards in the same row should have equal heights.

**3. Decision split card polish**
- Change the agreement label from "61.11% agent agreement" to a whole-number percentage with the counts, e.g. "61% agreement (11 of 18)". Compute it from the real counts; don't hardcode it.
- The card title and the meta text are squeezed side by side, which makes both wrap. Put the meta text on its own line under the title.

**4. Clickable Top 5 names**
- Every name in both Top 5 lists should select that customer, using the same selection handler as the sidebar (`selectedCustomerId`). Do not add a second selection path.
- Clicking a name should switch to the customer view, highlight that customer in the sidebar, and scroll their sidebar row into view.
- Render each name as a real button or link, so it works with the keyboard and shows a hover state and pointer cursor.

**Done when:**
- [ ] All five band labels are visible and no axis labels are clipped.
- [ ] The portfolio cards sit in a clean 2×2 grid.
- [ ] The agreement label shows a whole number with counts.
- [ ] Clicking any Top 5 name opens that customer, just like clicking them in the sidebar.
- [ ] Everything checks out in both light and dark mode.

When finished, update `memory/active-context.md` with the phase status.


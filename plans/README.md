# Animation plans

This folder records the selected animation work for FeedFlow's web dashboard and public landing page.

| # | Plan | Severity | Status |
|---|---|---|---|
| 001 | Restore the landing demo entrance | MEDIUM | DONE |
| 002 | Respect motion preferences and define the shared easing token | MEDIUM | DONE |
| 003 | Reveal native disclosure content | LOW | DONE |
| 004 | Animate RSS discovery results | LOW | DONE |
| 005 | Emphasize the selected channel in the landing preview | LOW | DONE |
| 006 | Add button press feedback in the dashboard | LOW | DONE |
| 007 | Preserve dashboard feedback with reduced motion | MEDIUM | DONE |
| 008 | Restore dashboard button press feedback | LOW | DONE |
| 009 | Reveal success notices and empty states | LOW | DONE |

## Recommended execution order

1. **002** first. It defines the shared --ease-out token and the reduced-motion rules used by the other plans.
2. **001** fixes the initial demo entrance on the landing page.
3. **003** adds disclosure-content transitions. Native details behavior remains the fallback in browsers without the required CSS support.
4. **004** animates the result panel and cards after RSS discovery.
5. **005** adds a local transition when the sample destination changes.
6. **006** adds a short press response to dashboard buttons.
7. **007** removes the dashboard-wide transition cutoff while retaining reduced-motion handling for movement.
8. **008** restores a short press response to enabled dashboard buttons.
9. **009** adds one-time entrances for success notices and empty states.

Plans 001, 003, 004, 005, and 006 depend on the token introduced by plan 002. Plans 003–006 also require its reduced-motion convention to be preserved.
Plans 007–009 use the motion and reduced-motion conventions already established by plan 002. Execute 007 before 008 and 009 so the dashboard no longer overrides component-level reduced-motion behavior. Plans 008 and 009 can then be executed in either order.

## Scope

The plans cover the FastAPI/Jinja web interface. Discord controls how its client UI is rendered; FeedFlow can animate only its own web pages and send animated media such as GIFs.

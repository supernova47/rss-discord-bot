# 007 — Preserve dashboard feedback with reduced motion

- **Status**: DONE
- **Commit**: 57272bc
- **Severity**: MEDIUM
- **Category**: Accessibility
- **Estimated scope**: 1 file, about 5 lines

## Problem

The dashboard's reduced-motion rule shortens every transition and animation in the dashboard subtree to .01ms. This removes useful color and selection feedback as well as movement. It also overrides the more deliberate reduced-motion rules on individual components.

Current rule in rssbot/static/dashboard.css:914:

~~~css
@media (prefers-reduced-motion: reduce) {
  .dashboard-body *,
  .dashboard-body *::before,
  .dashboard-body *::after {
    scroll-behavior: auto !important;
    transition-duration: .01ms !important;
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
  }
}
~~~

For example, dashboard buttons currently define 140ms color, border, and filter transitions in rssbot/static/dashboard.css:47–52, and selected RSS test entries define a 140ms background transition at line 516. The blanket rule makes both transitions effectively instantaneous for reduced-motion users. The shared stylesheet already handles button movement, disclosure chevrons, and RSS discovery under reduced motion at rssbot/static/style.css:70–73, 206–208, and 307–311.

## Target

Keep automatic scrolling disabled for reduced-motion users, but remove the universal duration and iteration overrides. Let each component retain useful feedback and explicitly remove only movement through its own reduced-motion rule.

~~~css
@media (prefers-reduced-motion: reduce) {
  .dashboard-body {
    scroll-behavior: auto !important;
  }
}
~~~

Do not add a dashboard-wide replacement that sets all transitions or animations to none or to a near-zero duration. Color, border, background, opacity, and other non-spatial feedback should retain its component-defined timing. Movement should be handled by focused component rules; plan 008 adds such a rule for dashboard button presses.

## Repo conventions to follow

- The shared strong ease-out token is --ease-out: cubic-bezier(0.23, 1, 0.32, 1) in rssbot/static/style.css:15.
- Existing reduced-motion rules are scoped to the animated component in rssbot/static/style.css:70–73, 206–208, and 307–311.
- Keep the dashboard scroll behavior override in rssbot/static/dashboard.css, where the current blanket rule is located.

## Steps

1. In rssbot/static/dashboard.css, replace the universal descendant rule inside the reduced-motion media query with the .dashboard-body scroll-behavior rule shown in Target.
2. Preserve component-specific reduced-motion rules in rssbot/static/style.css. Do not change their durations or scopes in this plan.
3. Confirm dashboard button color and filter transitions remain at their existing 140ms timing under reduced motion. Plan 008 will separately define the dashboard button movement override.

## Boundaries

- Do not change styles outside rssbot/static/dashboard.css.
- Do not change normal-motion transition timings or add new animations.
- Do not globally disable opacity, color, background, border, or selection feedback.
- Do not add dependencies or alter markup.
- If the reduced-motion block or cited component rules differ from these excerpts, stop and report the drift instead of improvising.

## Verification

- **Mechanical**: inspect rssbot/static/dashboard.css and confirm the reduced-motion block keeps scroll-behavior: auto but contains no universal transition-duration, animation-duration, or animation-iteration-count override.
- **Feel check**: emulate prefers-reduced-motion: reduce. Change a test-entry selection and hover/focus dashboard controls; confirm background and color feedback remain visible while the disclosure chevron and RSS discovery movement follow their existing reduced-motion rules.
- **Feel check**: emulate no-preference and confirm the dashboard's ordinary color transitions remain unchanged.
- **Done when**: reduced-motion mode keeps dashboard feedback at its defined timing and no longer overrides component-level motion rules.

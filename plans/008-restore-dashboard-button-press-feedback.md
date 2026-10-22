# 008 — Restore dashboard button press feedback

- **Status**: DONE
- **Commit**: 57272bc
- **Severity**: LOW
- **Category**: Cohesion & tokens
- **Estimated scope**: 1 file, about 8 lines

## Problem

The shared button style defines a subtle scale response on press in rssbot/static/style.css:67–68, but dashboard-specific rules suppress transforms for both hover and active states. The dashboard button transition also omits transform, so the shared press feedback cannot appear there.

Current dashboard rules in rssbot/static/dashboard.css:47–51 and 88–95:

~~~css
.dashboard-body .button {
  min-height: 38px;
  border-radius: 8px;
  font-size: 12px;
  transition: background 140ms ease, border-color 140ms ease, color 140ms ease, filter 140ms ease;
}

.dashboard-body .button:not(:disabled):hover,
.dashboard-body .button:not(:disabled):active {
  transform: none;
}

.dashboard-body .button:not(:disabled):active {
  filter: brightness(.92);
}
~~~

Current shared press exemplar in rssbot/static/style.css:63–73:

~~~css
.button { transition: transform 160ms var(--ease-out), background 160ms ease, border-color 160ms ease; }
.button:not(:disabled):active {
  transform: scale(.97);
}
@media (prefers-reduced-motion: reduce) {
  .button:not(:disabled):hover,
  .button:not(:disabled):active { transform: none; }
}
~~~

The dashboard's more specific selectors override the shared rule. The page currently gives a pressed button only a brightness filter.

## Target

Give enabled dashboard buttons the same restrained press response as shared buttons, while preserving the dashboard's existing hover behavior and brightness feedback. Keep the press transition at 160ms var(--ease-out), and keep color, border, and filter transitions at 140ms ease.

~~~css
.dashboard-body .button {
  transition:
    transform 160ms var(--ease-out),
    background 140ms ease,
    border-color 140ms ease,
    color 140ms ease,
    filter 140ms ease;
}

.dashboard-body .button:not(:disabled):hover {
  transform: none;
}

.dashboard-body .button:not(:disabled):active {
  transform: scale(.97);
  filter: brightness(.92);
}
~~~

Inside prefers-reduced-motion: reduce, add a focused override that keeps the existing color and filter transitions but removes transform motion:

~~~css
.dashboard-body .button {
  transition: background 140ms ease, border-color 140ms ease, color 140ms ease, filter 140ms ease;
}

.dashboard-body .button:not(:disabled):hover,
.dashboard-body .button:not(:disabled):active {
  transform: none;
}
~~~

## Repo conventions to follow

- Reuse --ease-out: cubic-bezier(0.23, 1, 0.32, 1) from rssbot/static/style.css:15.
- Shared buttons use transform scale(.97) with a 160ms ease-out transition in rssbot/static/style.css:63–73.
- Dashboard controls are compact and crisp; keep its hover lift suppressed and preserve its existing 140ms color and brightness feedback.
- Execute plan 007 first so the universal reduced-motion cutoff no longer masks the component-specific timing.

## Steps

1. In rssbot/static/dashboard.css, add transform 160ms var(--ease-out) to the dashboard button transition while preserving the four current 140ms transitions.
2. Split the combined hover/active transform rule: keep transform: none on enabled hover; use transform: scale(.97) on enabled active. Preserve filter: brightness(.92) on active.
3. Add the reduced-motion button overrides shown in Target to the existing reduced-motion media query.
4. Confirm disabled buttons remain excluded from both hover and press transforms.

## Boundaries

- Do not change button size, radius, colors, focus styling, disabled appearance, or hover lift behavior.
- Do not add press transforms to disabled buttons.
- Do not change shared button styles in rssbot/static/style.css.
- Do not add dependencies or alter markup.
- If the cited selectors or declarations differ, stop and report the drift instead of improvising.

## Verification

- **Mechanical**: inspect rssbot/static/dashboard.css and confirm enabled active buttons use scale(.97), their transform transition is 160ms var(--ease-out), disabled buttons are excluded, and the reduced-motion override removes transform.
- **Feel check**: press a dashboard button using mouse, touch emulation, and keyboard. Confirm the scale is subtle, releases smoothly, and does not add a hover lift.
- **Feel check**: emulate prefers-reduced-motion: reduce and confirm there is no button movement while color and brightness feedback remain.
- **Done when**: enabled dashboard buttons acknowledge a press with a short scale response and reduced-motion users receive no spatial movement.

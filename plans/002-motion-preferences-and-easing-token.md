# 002 — Respect motion preferences and define the shared easing token

- **Status**: DONE
- **Commit**: 57272bc
- **Severity**: MEDIUM
- **Category**: Accessibility
- **Estimated scope**: 2 files, about 25 lines

## Problem

The shared dashboard button rule lifts every hovered button, including on devices without a precise hover pointer. The shared stylesheet has no reduced-motion override. The advanced-settings chevron rotates with a transition but also has no reduced-motion handling. The landing page disables several transitions for reduced motion, but its button still shifts by one pixel while pressed.

Current shared tokens in rssbot/static/style.css:

~~~css
:root {
  color-scheme: dark;
  --bg: #0c0d13;
  --surface: #141620;
  --surface-raised: #1a1d29;
  --line: #292d3b;
  --text: #f3f4fb;
  --muted: #a0a4b4;
  --quiet: #8e94a5;
  --accent: #8c7cff;
  --accent-light: #b7adff;
  --green: #45d5a2;
  --red: #ff7582;
  --amber: #f1c365;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg);
  color: var(--text);
}
~~~

Current button and chevron transitions in rssbot/static/style.css:

~~~css
.button { min-height: 42px; padding: 0 16px; display: inline-flex; align-items: center; justify-content: center; gap: 9px; border: 1px solid transparent; border-radius: 10px; cursor: pointer; font-weight: 600; font-size: 13px; transition: transform .16s ease, background .16s ease, border-color .16s ease; white-space: nowrap; }
.button:hover { transform: translateY(-1px); }
.advanced-settings-chevron { flex: none; color: var(--accent-light); font-size: 20px; transition: transform .16s ease; }
~~~

Current landing button behavior in rssbot/static/landing.css:

~~~css
.landing-button:active {
  transform: translateY(1px);
}

@media (prefers-reduced-motion: reduce) {
  .landing-button,
  .landing-secondary-link,
  .landing-cta-invite,
  .landing-nav a,
  .landing-login-link,
  .landing-faq summary > span::before,
  .landing-faq summary > span::after {
    transition: none;
  }
}
~~~

## Target

Add the playbook's shared strong ease-out curve and limit button lift to devices that have a fine pointer and hover. Keep color feedback in reduced-motion mode while removing transform motion. The landing button should not shift while pressed when reduced motion is enabled.

~~~css
:root {
  --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
}

.button {
  transition: transform 160ms var(--ease-out), background 160ms ease, border-color 160ms ease;
}

@media (hover: hover) and (pointer: fine) {
  .button:not(:disabled):hover {
    transform: translateY(-1px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .button {
    transition: background 160ms ease, border-color 160ms ease;
  }

  .button:not(:disabled):hover,
  .button:not(:disabled):active {
    transform: none;
  }

  .advanced-settings-chevron {
    transition: none;
  }
}
~~~

Keep the existing landing reduced-motion rules and add this override inside that media query:

~~~css
  .landing-button:active {
    transform: none;
  }
~~~

The active-state guard is included now so plan 006 can add press feedback without creating a reduced-motion exception.

## Repo conventions to follow

- Shared color and surface tokens live in the :root block at the top of rssbot/static/style.css.
- CSS is plain and component selectors are grouped in the shared stylesheet; do not add an animation library.
- Use the exact playbook curve cubic-bezier(0.23, 1, 0.32, 1). Hover and color transitions use ease.

## Steps

1. Add --ease-out: cubic-bezier(0.23, 1, 0.32, 1) to the existing :root token block.
2. Update the shared button transition to use the token for transform and keep ease for background and border color.
3. Replace the unrestricted .button:hover transform with the fine-pointer hover media query shown above. Include :not(:disabled).
4. Add the reduced-motion override for shared buttons and the advanced settings chevron.
5. Extend the existing reduced-motion block in landing.css so .landing-button:active has transform:none.

## Boundaries

- Do not remove the button's color feedback or focus-visible outlines.
- Do not change landing entrance motion or the FAQ content; those belong to other plans.
- Do not add dependencies.
- If current selectors or token block differ from the excerpts, stop and report the drift.

## Verification

- **Mechanical**: search both stylesheets for prefers-reduced-motion. Confirm style.css now has the shared button/chevron rules, hover lift is inside the fine-pointer media query, and no transition: all was introduced.
- **Feel check**: test a mouse, keyboard, and touch viewport. The hover lift should appear only with a fine hover pointer. With reduced motion enabled, button colors still respond, but buttons and chevrons do not animate or shift.
- **Done when**: existing dashboard transform animations are disabled for reduced-motion users and the hover lift is unavailable on touch-only devices.

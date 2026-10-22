# 006 — Add dashboard button press feedback

- **Status**: DONE
- **Commit**: 57272bc
- **Severity**: LOW
- **Category**: Missed opportunities
- **Estimated scope**: 1 file, about 5 lines

## Problem

Dashboard buttons have a hover lift but no dedicated pressed state. On mouse, touch, or keyboard activation, there is no immediate visual response that the control was pressed.

Current button rules in rssbot/static/style.css:

~~~css
.button { min-height: 42px; padding: 0 16px; display: inline-flex; align-items: center; justify-content: center; gap: 9px; border: 1px solid transparent; border-radius: 10px; cursor: pointer; font-weight: 600; font-size: 13px; transition: transform .16s ease, background .16s ease, border-color .16s ease; white-space: nowrap; }
.button:hover { transform: translateY(-1px); }
~~~

## Target

Add a restrained scale press state to enabled dashboard buttons. Reuse the 160ms button transform transition and the shared strong ease-out token from plan 002.

~~~css
.button:not(:disabled):active {
  transform: scale(.97);
}
~~~

The .97 scale is within the playbook's 0.95–0.98 press-feedback range. Keep the rule after the hover rule so an active button uses the pressed state. Plan 002 already removes transform motion for reduced-motion users.

## Repo conventions to follow

- Shared button styling is in rssbot/static/style.css near lines 62–73.
- The design is a restrained admin dashboard; keep the press state subtle and use transform only.
- Execute plan 002 first so the transform transition uses --ease-out and the reduced-motion guard is in place.

## Steps

1. Add the enabled-button :active rule after the hover rule.
2. Confirm the button transition uses 160ms var(--ease-out) from plan 002.
3. Confirm the reduced-motion rule from plan 002 overrides both hover and active transforms.

## Boundaries

- Do not change button sizing, color, focus outlines, or hover behavior.
- Do not animate disabled buttons.
- Do not add dependencies.
- If the button selector or transition differs from the excerpt, stop and report the drift.

## Verification

- **Mechanical**: inspect style.css and confirm the :active selector excludes disabled buttons and targets transform only.
- **Feel check**: press buttons with mouse, touch emulation, and keyboard. Confirm the scale is brief and subtle, hover lift does not override the press, and the interface responds immediately. Enable reduced motion and confirm the button does not scale.
- **Done when**: enabled dashboard buttons visibly acknowledge a press without changing layout or disabled-button behavior.

# 009 — Reveal success notices and empty states

- **Status**: DONE
- **Commit**: 57272bc
- **Severity**: LOW
- **Category**: Missed opportunities
- **Estimated scope**: 1 file, about 20 lines

## Problem

Two infrequent dashboard states appear without motion:

- Successful save or update notices are rendered by rssbot/templates/guild.html:13. The server redirects back with a notice after successful actions in rssbot/web.py:840, 992, 1004, and 1068. The success message is useful feedback, but it appears as a static block.
- Empty states are rendered in rssbot/templates/home.html:71–82, rssbot/templates/guild.html:97–100, and rssbot/templates/test_select.html:27. These states explain first-run setup or recovery, but currently appear without a visual entrance.

The relevant current dashboard styling in rssbot/static/dashboard.css:102–117 and 214–219 is:

~~~css
.dashboard-body .notice {
  margin: 8px 0 14px;
  padding: 10px 12px;
  border: 1px solid rgba(160,164,180,.22);
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
}

.dashboard-body .notice-success {
  border-color: rgba(69,213,162,.28);
}

.dashboard-body .empty-state {
  margin: 26px 0 52px;
  padding: 34px 20px;
  border-radius: 12px;
  background: rgba(20,22,32,.35);
}
~~~

## Target

Add one-time CSS entrances to successful notices and empty-state panels. Use opacity and transform only: start at opacity: 0 and scale(.97), then transition to opacity: 1 and transform: none over 200ms var(--ease-out). Use @starting-style so the entry works without JavaScript and is skipped harmlessly by browsers that do not support it.

~~~css
.dashboard-body .notice-success,
.dashboard-body .empty-state {
  opacity: 1;
  transform: none;
  transition: opacity 200ms var(--ease-out), transform 200ms var(--ease-out);
}

@starting-style {
  .dashboard-body .notice-success,
  .dashboard-body .empty-state {
    opacity: 0;
    transform: scale(.97);
  }
}
~~~

In prefers-reduced-motion: reduce, preserve only a brief opacity entrance and remove scale movement:

~~~css
.dashboard-body .notice-success,
.dashboard-body .empty-state {
  transform: none;
  transition: opacity 160ms ease;
}

@starting-style {
  .dashboard-body .notice-success,
  .dashboard-body .empty-state {
    opacity: 0;
    transform: none;
  }
}
~~~

Put the reduced-motion starting style inside the reduced-motion media query. Do not stagger the elements; a page shows at most one of these states at a time.

## Repo conventions to follow

- Use --ease-out: cubic-bezier(0.23, 1, 0.32, 1) from rssbot/static/style.css:15 for entering UI.
- Existing CSS-only entrances use @starting-style, opacity, transform, and 200ms var(--ease-out) in rssbot/static/style.css:275–304.
- Existing reduced-motion rules are component-scoped in rssbot/static/style.css:206–224 and 307–311.
- Execute plan 007 first so the dashboard-wide reduced-motion rule does not collapse the opacity feedback to .01ms.

## Steps

1. In rssbot/static/dashboard.css, add the normal-motion success-notice and empty-state transition plus the @starting-style rule shown in Target.
2. Add a prefers-reduced-motion: reduce rule for the same two selectors. Keep the 160ms ease opacity transition, force transform: none, and set a matching @starting-style with opacity: 0 and transform: none.
3. Keep the implementation CSS-only; do not add classes, timers, JavaScript, or markup changes.
4. Confirm the selectors do not include feed-filter-empty or dynamically changing search results.

## Boundaries

- Do not animate error or warning notices.
- Do not animate individual feed rows, search/filter results, or frequent updates.
- Do not add stagger, blur, layout-property transitions, or dependencies.
- Do not alter template structure or server behavior.
- If the templates or class names differ from the cited excerpts, stop and report the drift instead of improvising.

## Verification

- **Mechanical**: inspect rssbot/static/dashboard.css and confirm only .dashboard-body .notice-success and .dashboard-body .empty-state receive the entrance styles; motion uses opacity and transform only; durations are 200ms normally and 160ms for reduced-motion opacity.
- **Feel check**: load a guild page after a successful save and open pages with empty server, feed, and RSS test results. Confirm each visible state enters once, subtly, without delaying interaction.
- **Feel check**: emulate prefers-reduced-motion: reduce. Confirm the states fade without scaling or spatial movement. Emulate no-preference and confirm they fade and scale from .97 to their natural size.
- **Done when**: success and first-run/recovery states appear with a brief, calm entrance, while frequent search and feed changes remain immediate.

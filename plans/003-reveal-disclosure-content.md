# 003 — Reveal native disclosure content

- **Status**: DONE
- **Commit**: 57272bc
- **Severity**: LOW
- **Category**: Missed opportunities
- **Estimated scope**: 2 files, about 20 lines

## Problem

The advanced-settings panel and landing FAQ use native details disclosures. Their content appears or disappears immediately, while the associated chevrons rotate over 160ms or 200ms. This separates the indicator's motion from the content change.

Current advanced-settings disclosure in rssbot/templates/feed_form.html:

~~~html
    <details class="advanced-settings" {% if feed or error %}open{% endif %}>
      <summary class="advanced-settings-summary">
        <span class="advanced-settings-copy">
          <strong>{% if language == 'en' %}Optional settings{% else %}Дополнительные настройки{% endif %}</strong>
          <small>{% if language == 'en' %}Polling interval, sender profile, and post appearance{% else %}Интервал проверки, профиль отправителя и оформление публикации{% endif %}</small>
        </span>
        <span class="advanced-settings-chevron" aria-hidden="true">⌄</span>
      </summary>

      <section class="form-section">
~~~

Current FAQ icon transition and answer styling in rssbot/static/landing.css:

~~~css
.landing-faq-list summary > span::before,
.landing-faq-list summary > span::after {
  content: "";
  width: 15px;
  height: 2px;
  position: absolute;
  top: 7px;
  left: 1px;
  border-radius: 2px;
  background: #d0cbf8;
  transition: transform .2s ease;
}

.landing-faq-list summary > span::after {
  transform: rotate(90deg);
}

.landing-faq-list details[open] summary > span::after {
  transform: rotate(0);
}

.landing-faq-list details > p {
  max-width: 60ch;
  margin: -1px 40px 0 0;
  padding: 0 0 22px;
  color: #d1d2df;
  font-size: 16px;
  line-height: 1.55;
}
~~~

Current advanced-settings chevron transition in rssbot/static/style.css:

~~~css
.advanced-settings-chevron { flex: none; color: var(--accent-light); font-size: 20px; transition: transform .16s ease; }
.advanced-settings[open] .advanced-settings-chevron { transform: rotate(180deg); }
~~~

## Target

For browsers that support the native details-content pseudo-element, fade and scale its content in and out over 200ms. Keep native details behavior as the fallback. Do not animate height, margins, or padding; the content can still cause a layout change when the disclosure toggles.

~~~css
@supports selector(::details-content) {
  @media (prefers-reduced-motion: no-preference) {
    .advanced-settings::details-content,
    .landing-faq-list details::details-content {
      opacity: 0;
      transform: scale(.97);
      transform-origin: top center;
      transition:
        opacity 200ms var(--ease-out),
        transform 200ms var(--ease-out),
        content-visibility 200ms allow-discrete;
    }

    .advanced-settings[open]::details-content,
    .landing-faq-list details[open]::details-content {
      opacity: 1;
      transform: none;
    }
  }
}
~~~

The 200ms duration is within the playbook's 150–250ms dropdown range. The initial scale .97 is within its recommended 0.9–0.97 range.

## Repo conventions to follow

- Existing disclosure behavior is native HTML details; do not replace it with custom JavaScript.
- Shared reduced-motion/easing rules are established by rssbot/static/style.css in plan 002.
- The progressive CSS enhancement uses the documented ::details-content pseudo-element and leaves unsupported browsers on the native instant open/close behavior. Reference: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/details and https://developer.chrome.com/blog/styling-details

## Steps

1. Add the @supports selector(::details-content) enhancement to style.css for .advanced-settings.
2. Add the same enhancement to landing.css for .landing-faq-list details.
3. Use only opacity, transform, and the discrete content-visibility transition. Keep the existing open/closed marker and chevron state.
4. Keep the animation inside prefers-reduced-motion: no-preference. Do not alter the native details markup.

## Boundaries

- Do not animate height, width, padding, margin, or the whole page.
- Do not add JavaScript listeners or dependencies for disclosures.
- Do not remove the native details interaction or keyboard support.
- If browser support or selectors differ from the cited source excerpts, stop and report the drift.

## Verification

- **Mechanical**: inspect both CSS files. Confirm the enhancement is guarded by @supports selector(::details-content) and prefers-reduced-motion: no-preference, and the transition lists only opacity, transform, and content-visibility.
- **Feel check**: open and close the advanced-settings panel and FAQ with mouse and keyboard. Confirm the content softly appears and disappears with the icon; test a browser without ::details-content support and confirm native disclosures still work.
- **Done when**: supported browsers animate disclosure content in both directions, while unsupported browsers and reduced-motion users retain immediate native disclosure behavior.

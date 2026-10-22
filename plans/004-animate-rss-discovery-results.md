# 004 — Animate RSS discovery results

- **Status**: DONE
- **Commit**: 57272bc
- **Severity**: LOW
- **Category**: Missed opportunities
- **Estimated scope**: 2 files, about 25 lines

## Problem

The RSS search panel becomes visible as soon as the user requests discovery, and candidate cards are appended after the fetch. Neither state change has an entrance transition.

Current panel styles in rssbot/static/style.css:

~~~css
.feed-discovery-results { margin-top: 11px; padding: 11px; border: 1px solid #303445; border-radius: 9px; background: rgba(255,255,255,.02); }
.feed-discovery-results[hidden] { display: none; }
.feed-discovery-options { display: grid; gap: 8px; }
.feed-discovery-option { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px; border: 1px solid #303445; border-radius: 8px; background: rgba(16,18,26,.65); }
~~~

Current visibility and candidate insertion in rssbot/static/feed_discovery.js:

~~~js
    trigger.disabled = true;
    trigger.textContent = labels.searching;
    results.hidden = false;
    status.textContent = labels.searching;
    options.replaceChildren();
~~~

~~~js
      status.textContent = labels.found(candidates.length);
      for (const candidate of candidates) {
        const card = document.createElement("article");
        card.className = "feed-discovery-option";
~~~

The candidate card is populated before it is appended. Current ending lines:

~~~js
        actions.append(select, preview);
        card.append(copy, actions);
        options.append(card);
      }
~~~

## Target

Fade and scale the results panel and each new candidate card into place. Use @starting-style for first appearance, display with allow-discrete for the hidden panel, and stagger cards by 50ms with a 200ms cap. Unsupported browsers should keep the current immediate display behavior.

~~~css
@supports (transition-behavior: allow-discrete) {
  .feed-discovery-results {
    opacity: 1;
    transform: none;
    transition:
      opacity 200ms var(--ease-out),
      transform 200ms var(--ease-out),
      display 200ms allow-discrete;
  }

  .feed-discovery-results[hidden] {
    display: none;
    opacity: 0;
    transform: scale(.97);
  }

  .feed-discovery-option {
    opacity: 1;
    transform: none;
    transition: opacity 200ms var(--ease-out), transform 200ms var(--ease-out);
    transition-delay: var(--feed-stagger, 0ms);
  }

  @starting-style {
    .feed-discovery-results:not([hidden]),
    .feed-discovery-option {
      opacity: 0;
      transform: scale(.97);
    }
  }
}

@media (prefers-reduced-motion: reduce) {
  .feed-discovery-results,
  .feed-discovery-option {
    transition: none;
    transition-delay: 0ms;
  }
}
~~~

For each candidate, set a capped delay before appending:

~~~js
      status.textContent = labels.found(candidates.length);
      for (const [index, candidate] of candidates.entries()) {
        const card = document.createElement("article");
        card.className = "feed-discovery-option";
        const staggerIndex = Math.min(index, 4);
        card.style.setProperty("--feed-stagger", (staggerIndex * 50) + "ms");
        // Keep the existing candidate card construction here.
      }
~~~

The 200ms duration is within the playbook's small-popover range; the 50ms stagger is within its recommended 30–80ms range. The .97 starting scale follows its recommended entrance range. For transitioning from display:none, @starting-style and allow-discrete are required. Reference: https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Transitions/Using

## Repo conventions to follow

- Feed discovery styles are adjacent in rssbot/static/style.css near lines 231–242.
- Feed discovery behavior is vanilla JavaScript in rssbot/static/feed_discovery.js; preserve hidden and aria-live semantics.
- Reuse --ease-out from plan 002.

## Steps

1. Add the panel and card transition rules to the existing feed-discovery CSS group.
2. Keep the hidden selector's display:none behavior and add opacity/transform states plus display allow-discrete inside the feature-support block.
3. Add the @starting-style states for the newly visible panel and newly inserted cards.
4. Change the candidate loop to entries(), set the 50ms capped stagger, then append each fully populated card.
5. Add the reduced-motion override after the transition rules and clear all stagger delays there.

## Boundaries

- Do not animate search/filter rows or every typed character.
- Do not change fetch behavior, status copy, candidate order, or candidate content.
- Do not add dependencies.
- If the current loop or CSS selectors differ from the excerpts, stop and report the drift.

## Verification

- **Mechanical**: run node --check rssbot/static/feed_discovery.js. Inspect the CSS to confirm transitions use only opacity, transform, and display; confirm reduced-motion removes transitions and delays.
- **Feel check**: in the feed editor, run RSS discovery with zero, one, and several candidates. Confirm the loading panel enters once, cards arrive in source order with a small stagger, and repeated discovery does not leave stale cards. Enable reduced motion and confirm results appear immediately.
- **Done when**: panel and card entrances are visible but quick, keyboard controls remain usable immediately, and reduced-motion users see no movement.

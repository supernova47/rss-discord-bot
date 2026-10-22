# 005 — Emphasize the selected channel in the landing preview

- **Status**: DONE
- **Commit**: 57272bc
- **Severity**: LOW
- **Category**: Missed opportunities
- **Estimated scope**: 2 files, about 20 lines

## Problem

Changing either channel selector updates the Discord preview destination by replacing textContent immediately. The page explicitly tells users that the sample destination updates, but the preview gives no visual cue linking the selection to the changed value.

The following excerpt shows the English branch. The application keeps its Russian localization.

Current update logic in rssbot/static/landing.js:

~~~js
  const updateChannel = (value) => {
    const source = channelSelects.find((select) => select.value === value) ?? channelSelects[0];
    if (!source) return;

    for (const select of channelSelects) select.value = source.value;
    const label = source.options[source.selectedIndex]?.textContent?.trim();
    if (!label) return;
    for (const output of channelOutputs) output.textContent = label;
  };
~~~

The destination output in rssbot/templates/landing.html is already a polite live region:

~~~html
<p class="landing-discord-channel">Posts in <strong data-channel-output aria-live="polite"># news</strong></p>
~~~

## Target

After a real value change, give only the destination label a small opacity-and-scale pulse. Use a CSS transition, not keyframes, so another change retargets the current state. Keep the live-region markup and update its text immediately.

~~~css
[data-channel-output] {
  transition: opacity 160ms var(--ease-out), transform 160ms var(--ease-out);
}

[data-channel-output].is-updating {
  opacity: .75;
  transform: scale(.97);
}

@media (prefers-reduced-motion: reduce) {
  [data-channel-output] {
    transition: opacity 160ms ease;
  }
}
~~~

In landing.js, skip outputs whose text already matches the new label. For changed outputs, clear the prior timer in a WeakMap, set the new text, add is-updating, and remove that class after 80ms. Store the new timer per output so rapid selector changes leave the class active until the latest change has had its brief highlight. The reduced-motion rule leaves opacity feedback and removes transform because the transform exists only in the normal-motion rule.

## Repo conventions to follow

- Landing-specific visual styles belong in rssbot/static/landing.css.
- State synchronization belongs in rssbot/static/landing.js.
- The page already uses aria-live="polite" on the destination output; do not replace or duplicate that announcement.
- Reuse --ease-out from plan 002.

## Steps

1. Add a WeakMap for the pending update timer near the channel selector/output declarations.
2. In updateChannel, compare each output's trimmed text to label and skip unchanged outputs.
3. For changed outputs, clear any previous timer, update textContent immediately, add is-updating, and schedule class removal after 80ms.
4. Add the normal-motion transition and transient styles to landing.css, followed by the reduced-motion opacity-only transition.
5. Keep select synchronization and all other landing reveal behavior unchanged.

Implementation note: the destination label is an inline `<strong>` element. It uses `display: inline-block` so its scale transform is rendered.

## Boundaries

- Do not animate the full Discord message or delay the selected label update.
- Do not use CSS keyframes or add a motion library.
- Do not change the live-region markup or its announcement.
- If channel synchronization has changed from the excerpt, stop and report the drift.

## Verification

- **Mechanical**: run node --check rssbot/static/landing.js. Confirm no animation keyframes were added and the text update remains synchronous.
- **Feel check**: change the sample channel using both selectors, including switching rapidly back and forth. Confirm only the preview destination responds, the mirrored selector remains synchronized, and the animation does not restart from a stale timer. Enable reduced motion and confirm no scale movement.
- **Done when**: changed destination labels get a subtle, short pulse; unchanged initial values do not pulse; the live region announces each changed label once.

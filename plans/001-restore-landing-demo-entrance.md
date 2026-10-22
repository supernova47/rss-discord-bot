# 001 — Restore the landing demo entrance

- **Status**: DONE
- **Commit**: 57272bc
- **Severity**: MEDIUM
- **Category**: Purpose & frequency
- **Estimated scope**: 2 files, about 20 lines

## Problem

The landing demo's starting styles are enabled only after the root element receives the js class, but the script adds the final is-in state first. The demo therefore has no hidden starting frame for its entrance transition. The intended clip-path and scale transitions in the CSS do not explain a visible entry.

Current script in rssbot/static/landing.js:

~~~js
  if (stage) {
    stage.classList.add('is-in');
  }
  for (const item of revealItems) observer.observe(item);
  document.documentElement.classList.add('js');
~~~

Current entrance styles in rssbot/static/landing.css:

~~~css
  .js .landing-stage[data-shutter] {
    clip-path: inset(0 0 100% 0);
    transition: clip-path 1100ms cubic-bezier(.77, 0, .18, 1);
  }

  .js .landing-stage[data-shutter].is-in {
    clip-path: inset(0);
  }

  .js .landing-demo {
    transform: scale(1.025);
    transition: transform 1500ms cubic-bezier(.22, 1, .36, 1);
  }

  .js .landing-stage.is-in .landing-demo {
    transform: none;
  }
~~~

## Target

Apply the js class before revealing the stage, then add is-in on the next animation frame so the browser sees the starting state. Replace the shutter with an opacity and transform entrance on the demo. Keep the existing reduced-motion and no-IntersectionObserver early-return paths that show content immediately.

~~~css
@media (prefers-reduced-motion: no-preference) {
  .js .landing-demo {
    opacity: 0;
    transform: scale(.97);
    transition: opacity 250ms var(--ease-out), transform 250ms var(--ease-out);
  }

  .js .landing-stage.is-in .landing-demo {
    opacity: 1;
    transform: none;
  }
}
~~~

The 250ms duration is below the playbook's 300ms UI ceiling. The starting scale .97 follows its recommended 0.9–0.97 entrance range. Remove the clip-path transition and the old 1500ms nested scale transition.

## Repo conventions to follow

- Landing styles live in rssbot/static/landing.css; the page behavior lives in rssbot/static/landing.js.
- Existing scroll reveals already transition opacity and transform in landing.css near lines 905–914.
- Plan 002 adds the shared --ease-out token with the value cubic-bezier(0.23, 1, 0.32, 1). Execute plan 002 first.

## Steps

1. In the normal-motion branch of landing.js, add the js class before observing reveal items and before setting the stage's is-in state.
2. Schedule stage.classList.add('is-in') with requestAnimationFrame after the js class is present. Do not delay the reduced-motion or missing-IntersectionObserver fallback.
3. In landing.css, remove the stage clip-path entrance and nested demo scale rules. Use the target opacity and scale transition above inside the existing no-preference media query.
4. Keep the FAQ, hero-copy, and scroll-reveal timings outside this plan unchanged.

## Boundaries

- Do not touch templates, server routes, or any other animation.
- Do not add dependencies.
- If the script or selectors differ from the excerpts, stop and report the drift.

## Verification

- **Mechanical**: run node --check rssbot/static/landing.js. Inspect landing.css and confirm this entrance transitions only opacity and transform, has no clip-path transition, and uses the --ease-out token from plan 002.
- **Feel check**: open the landing page with reduced motion disabled and reload. Confirm the demo is visible after a short, clear scale-and-fade entrance, with no shutter wipe or long settling motion. Enable reduced motion and reload; confirm the demo is immediately visible.
- **Done when**: the normal-motion entrance runs once on page load, and the reduced-motion fallback never hides the demo.

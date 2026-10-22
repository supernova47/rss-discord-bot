const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.resolve(__dirname, "..");
const read = (relativePath) => fs.readFileSync(path.join(root, relativePath), "utf8");

function createClassList() {
  const values = new Set();
  return {
    add(value) { values.add(value); },
    remove(value) { values.delete(value); },
    contains(value) { return values.has(value); },
  };
}

function runLanding({ reduceMotion = false, stage = null, channelSelects = [], channelOutputs = [], revealItems = [] } = {}) {
  const rootClassList = createClassList();
  const animationFrames = [];
  let timerId = 0;
  const observedItems = [];
  const timers = new Map();
  const clearedTimers = [];
  const document = {
    documentElement: { classList: rootClassList },
    querySelector(selector) { return selector === "[data-shutter]" ? stage : null; },
    querySelectorAll(selector) {
      if (selector === "[data-channel-select]") return channelSelects;
      if (selector === "[data-channel-output]") return channelOutputs;
      if (selector === "[data-reveal-item]") return revealItems;
      return [];
    },
  };
  const window = { matchMedia: () => ({ matches: reduceMotion }), dispatchEvent() {} };
  class IntersectionObserverFake {
    constructor(callback) { this.callback = callback; }
    observe(item) { observedItems.push(item); }
    unobserve() {}
  }
  window.IntersectionObserver = IntersectionObserverFake;

  require("node:vm").runInNewContext(read("rssbot/static/landing.js"), {
    document,
    window,
    IntersectionObserver: IntersectionObserverFake,
    requestAnimationFrame(callback) { animationFrames.push(callback); },
    Map,
    WeakMap,
    setTimeout(callback, delay) {
      const id = ++timerId;
      timers.set(id, { callback, delay });
      return id;
    },
    clearTimeout(id) { clearedTimers.push(id); },
  });
  return {
    rootClassList,
    stage,
    observedItems,
    timers,
    clearedTimers,
    runAnimationFrame: () => animationFrames.shift()?.(),
    pendingAnimationFrames: () => animationFrames.length,
    runTimer: (id) => timers.get(id)?.callback(),
  };
}

function createChannelSelect(value) {
  const listeners = new Map();
  const options = [
    { value: "news", textContent: "# news" },
    { value: "updates", textContent: "# updates" },
  ];
  return {
    options,
    value,
    get selectedIndex() { return options.findIndex((option) => option.value === this.value); },
    addEventListener(name, callback) { listeners.set(name, callback); },
    listener(name) { return listeners.get(name); },
  };
}

function createElement() {
  const listeners = new Map();
  const children = [];
  const styles = new Map();
  return {
    children,
    dataset: {},
    disabled: false,
    hidden: false,
    options: [],
    selectedIndex: 0,
    style: { setProperty(name, value) { styles.set(name, value); }, getPropertyValue(name) { return styles.get(name) ?? ""; } },
    textContent: "",
    value: "",
    addEventListener(name, callback) { listeners.set(name, callback); },
    dispatchEvent() {},
    focus() {},
    append(...items) { children.push(...items); },
    replaceChildren(...items) { children.splice(0, children.length, ...items); },
    listener(name) { return listeners.get(name); },
  };
}

function createDiscoveryHarness(candidateResponses) {
  const rootElement = createElement();
  rootElement.dataset.endpoint = "/feed-discovery";
  const trigger = createElement();
  const results = createElement();
  results.hidden = true;
  const status = createElement();
  const options = createElement();
  const urlInput = createElement();
  urlInput.value = "https://example.test";
  const titleInput = createElement();
  const csrfInput = createElement();
  csrfInput.value = "csrf";
  const elements = new Map([
    ["feed-discovery", rootElement],
    ["discover-feed", trigger],
    ["feed-discovery-results", results],
    ["feed-discovery-status", status],
    ["feed-discovery-options", options],
  ]);
  const queries = new Map([
    ['input[name="url"]', urlInput],
    ['input[name="title"]', titleInput],
    ['input[name="csrf_token"]', csrfInput],
  ]);
  let responseIndex = 0;
  const document = {
    documentElement: { lang: "ru" },
    getElementById(id) { return elements.get(id) ?? null; },
    querySelector(selector) { return queries.get(selector) ?? null; },
    createElement() { return createElement(); },
  };
  const window = { dispatchEvent() {} };
  const vm = require("node:vm");
  vm.runInNewContext(read("rssbot/static/feed_discovery.js"), {
    document,
    window,
    URLSearchParams,
    Event: class EventFake {},
    CustomEvent: class CustomEventFake {},
    fetch: async () => ({
      ok: true,
      json: async () => ({ candidates: candidateResponses[responseIndex++] }),
    }),
  });

  return { trigger, results, status, options };
}

function blockAfter(source, marker) {
  const markerIndex = source.indexOf(marker);
  assert.notEqual(markerIndex, -1, `expected to find ${marker}`);
  const openIndex = source.indexOf("{", markerIndex);
  assert.notEqual(openIndex, -1, `expected an opening brace after ${marker}`);

  let depth = 1;
  for (let index = openIndex + 1; index < source.length; index += 1) {
    if (source[index] === "{") depth += 1;
    if (source[index] === "}") depth -= 1;
    if (depth === 0) return source.slice(openIndex + 1, index);
  }

  assert.fail(`expected a closing brace for ${marker}`);
}

test("shared motion respects fine pointers and reduced-motion preferences", () => {
  const dashboardCss = read("rssbot/static/style.css");
  const landingCss = read("rssbot/static/landing.css");
  const rootTokens = blockAfter(dashboardCss, ":root");
  const buttonRule = blockAfter(dashboardCss, ".button {");
  const finePointerRule = blockAfter(dashboardCss, "@media (hover: hover) and (pointer: fine)");
  const reducedMotionRule = blockAfter(dashboardCss, "@media (prefers-reduced-motion: reduce)");
  const landingReducedMotionRule = blockAfter(landingCss, "@media (prefers-reduced-motion: reduce)");

  assert.match(rootTokens, /--ease-out:\s*cubic-bezier\(0\.23,\s*1,\s*0\.32,\s*1\)/);
  assert.match(buttonRule, /transition:\s*transform 160ms var\(--ease-out\),\s*background 160ms ease,\s*border-color 160ms ease/);
  assert.match(finePointerRule, /\.button:not\(:disabled\):hover\s*\{[^}]*transform:\s*translateY\(-1px\)/s);
  assert.doesNotMatch(dashboardCss, /\.button:hover\s*\{[^}]*transform:/s);
  assert.match(reducedMotionRule, /\.button\s*\{[^}]*transition:\s*background 160ms ease,\s*border-color 160ms ease/s);
  assert.match(reducedMotionRule, /\.button:not\(:disabled\):hover,\s*\.button:not\(:disabled\):active\s*\{[^}]*transform:\s*none/s);
  const chevronBaseIndex = dashboardCss.indexOf(".advanced-settings-chevron {");
  const chevronReducedIndex = dashboardCss.indexOf(".advanced-settings-chevron {", chevronBaseIndex + 1);
  assert.ok(chevronBaseIndex >= 0 && chevronReducedIndex > chevronBaseIndex);
  assert.match(dashboardCss.slice(chevronBaseIndex, chevronReducedIndex), /transition:\s*transform \.16s ease/);
  const chevronReducedMedia = dashboardCss.indexOf("@media (prefers-reduced-motion: reduce)", chevronReducedIndex);
  assert.ok(chevronReducedMedia > chevronReducedIndex);
  assert.match(blockAfter(dashboardCss.slice(chevronReducedMedia), "@media (prefers-reduced-motion: reduce)"), /\.advanced-settings-chevron\s*\{[^}]*transition:\s*none/s);
  assert.match(landingReducedMotionRule, /\.landing-button:active\s*\{[^}]*transform:\s*none/s);
  assert.doesNotMatch(dashboardCss + landingCss, /transition:\s*all\b/);
});

test("landing demo waits two frames so its hidden state can render before entering", () => {
  const stage = { classList: createClassList() };
  const landing = runLanding({ stage });

  assert.equal(landing.rootClassList.contains("js"), true);
  assert.equal(stage.classList.contains("is-in"), false);
  assert.equal(landing.pendingAnimationFrames(), 1);
  landing.runAnimationFrame();
  assert.equal(stage.classList.contains("is-in"), false);
  assert.equal(landing.pendingAnimationFrames(), 1);
  landing.runAnimationFrame();
  assert.equal(stage.classList.contains("is-in"), true);
});

test("landing demo stays immediately visible when reduced motion is enabled", () => {
  const stage = { classList: createClassList() };
  const landing = runLanding({ reduceMotion: true, stage });

  assert.equal(stage.classList.contains("is-in"), true);
  assert.equal(landing.rootClassList.contains("js"), false);
});

test("native disclosure content transitions only when motion and browser support allow it", () => {
  const dashboardCss = read("rssbot/static/style.css");
  const landingCss = read("rssbot/static/landing.css");

  for (const [css, selector] of [
    [dashboardCss, ".advanced-settings::details-content"],
    [landingCss, ".landing-faq-list details::details-content"],
  ]) {
    const supportBlock = blockAfter(css, "@supports selector(::details-content)");
    const motionBlock = blockAfter(supportBlock, "@media (prefers-reduced-motion: no-preference)");
    const contentRule = blockAfter(motionBlock, selector);

    assert.match(contentRule, /opacity:\s*0/);
    assert.match(contentRule, /transform:\s*scale\(\.97\)/);
    assert.match(contentRule, /transition:[\s\S]*opacity 200ms var\(--ease-out\)[\s\S]*transform 200ms var\(--ease-out\)[\s\S]*content-visibility 200ms allow-discrete/);
    assert.doesNotMatch(contentRule, /(?:height|width|padding|margin)\s*:/);
  }
});

test("RSS discovery results and cards use a capped stagger and replace stale results", async () => {
  const candidates = Array.from({ length: 6 }, (_, index) => ({
    title: `Source ${index}`,
    url: `https://example.test/${index}.xml`,
  }));
  const discovery = createDiscoveryHarness([candidates, [candidates[0]]]);

  await discovery.trigger.listener("click")();
  assert.equal(discovery.results.hidden, false);
  assert.deepEqual(
    discovery.options.children.map((card) => card.style.getPropertyValue("--feed-stagger")),
    ["0ms", "50ms", "100ms", "150ms", "200ms", "200ms"],
  );
  assert.deepEqual(
    discovery.options.children.map((card) => card.children[0].children[0].textContent),
    candidates.map((candidate) => candidate.title),
  );

  await discovery.trigger.listener("click")();
  assert.equal(discovery.options.children.length, 1);
  assert.equal(discovery.options.children[0].children[0].children[0].textContent, "Source 0");
});

test("RSS discovery motion is progressive and disabled for reduced-motion users", () => {
  const dashboardCss = read("rssbot/static/style.css");
  const supportBlock = blockAfter(dashboardCss, "@supports (transition-behavior: allow-discrete)");
  const panelRule = blockAfter(supportBlock, ".feed-discovery-results {");
  const cardRule = blockAfter(supportBlock, ".feed-discovery-option {");
  const startingStyle = blockAfter(supportBlock, "@starting-style");

  assert.match(panelRule, /opacity 200ms var\(--ease-out\)/);
  assert.match(panelRule, /transform 200ms var\(--ease-out\)/);
  assert.match(panelRule, /display 200ms allow-discrete/);
  assert.match(cardRule, /transition-delay:\s*var\(--feed-stagger, 0ms\)/);
  assert.match(startingStyle, /\.feed-discovery-results:not\(\[hidden\]\)/);
  assert.match(startingStyle, /\.feed-discovery-option/);
  assert.match(dashboardCss, /@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.feed-discovery-results,[\s\S]*?\.feed-discovery-option\s*\{[^}]*transition:\s*none;[^}]*transition-delay:\s*0ms;/);
});

test("landing channel preview pulses only changed labels and cancels stale timers", () => {
  const selects = [createChannelSelect("news"), createChannelSelect("news")];
  const output = { textContent: "# news", classList: createClassList() };
  const landing = runLanding({ channelSelects: selects, channelOutputs: [output] });

  assert.equal(output.classList.contains("is-updating"), false);
  assert.equal(landing.timers.size, 0);

  selects[0].value = "updates";
  selects[0].listener("change")();
  const firstTimerId = Math.max(...landing.timers.keys());
  assert.equal(output.textContent, "# updates");
  assert.equal(output.classList.contains("is-updating"), true);
  assert.deepEqual(selects.map((select) => select.value), ["updates", "updates"]);
  assert.equal(landing.timers.get(firstTimerId).delay, 80);

  selects[0].value = "news";
  selects[0].listener("change")();
  const latestTimerId = Math.max(...landing.timers.keys());
  assert.deepEqual(selects.map((select) => select.value), ["news", "news"]);
  assert.equal(output.textContent, "# news");
  assert.equal(output.classList.contains("is-updating"), true);
  assert.ok(landing.clearedTimers.includes(firstTimerId));

  landing.runTimer(latestTimerId);
  assert.equal(output.classList.contains("is-updating"), false);
});

test("landing channel pulse keeps text synchronous and limits scale to motion-friendly users", () => {
  const landingCss = read("rssbot/static/landing.css");
  const reducedMotionRule = blockAfter(landingCss, "@media (prefers-reduced-motion: reduce)");
  const noPreferenceIndex = landingCss.lastIndexOf("@media (prefers-reduced-motion: no-preference)");
  assert.ok(noPreferenceIndex >= 0);
  const noPreferenceRule = blockAfter(landingCss.slice(noPreferenceIndex), "@media (prefers-reduced-motion: no-preference)");
  const baseRule = blockAfter(landingCss, "[data-channel-output] {");
  const updatingRule = blockAfter(landingCss, "[data-channel-output].is-updating");
  const motionOutputRule = blockAfter(noPreferenceRule, "[data-channel-output] {");
  const motionUpdatingRule = blockAfter(noPreferenceRule, "[data-channel-output].is-updating");

  assert.match(baseRule, /opacity 160ms var\(--ease-out\)/);
  assert.match(updatingRule, /opacity:\s*\.75/);
  assert.doesNotMatch(updatingRule, /transform:/);
  assert.match(motionOutputRule, /transform 160ms var\(--ease-out\)/);
  assert.match(motionUpdatingRule, /transform:\s*scale\(\.97\)/);
  assert.match(reducedMotionRule, /\[data-channel-output\]\s*\{[^}]*transition:\s*opacity 160ms ease/s);
  assert.doesNotMatch(reducedMotionRule, /\[data-channel-output\](?:\.is-updating)?\s*\{[^}]*transform:/s);
});

test("enabled dashboard buttons use restrained press feedback", () => {
  const dashboardCss = read("rssbot/static/style.css");
  const pressRule = /\.button:not\(:disabled\):active\s*\{\s*transform:\s*scale\(\.97\);\s*\}/.exec(dashboardCss);
  const hoverIndex = dashboardCss.indexOf(".button:not(:disabled):hover");

  assert.ok(pressRule, "enabled buttons should scale slightly while pressed");
  assert.ok(pressRule.index > hoverIndex);
});

test("dashboard reduced motion keeps scrolling disabled without erasing component feedback", () => {
  const dashboardCss = read("rssbot/static/dashboard.css");
  const reducedMotionRule = blockAfter(dashboardCss, "@media (prefers-reduced-motion: reduce)");

  assert.match(reducedMotionRule, /\.dashboard-body\s*\{[^}]*scroll-behavior:\s*auto\s*!important/s);
  assert.doesNotMatch(reducedMotionRule, /transition-duration:\s*\.01ms|animation-duration:\s*\.01ms|animation-iteration-count:\s*1/);
  assert.doesNotMatch(reducedMotionRule, /\.dashboard-body\s+\*\s*,/);

  const buttonRule = blockAfter(dashboardCss, ".dashboard-body .button {");
  const testEntryRule = blockAfter(dashboardCss, ".dashboard-body .test-entry {");
  assert.match(buttonRule, /background 140ms ease/);
  assert.match(buttonRule, /filter 140ms ease/);
  assert.match(testEntryRule, /background 140ms ease/);
});

test("dashboard buttons press briefly and remove only spatial motion for reduced motion", () => {
  const dashboardCss = read("rssbot/static/dashboard.css");
  const buttonRule = blockAfter(dashboardCss, ".dashboard-body .button {");
  const activeRule = blockAfter(dashboardCss, ".dashboard-body .button:not(:disabled):active {");
  const reducedMotionRule = blockAfter(dashboardCss, "@media (prefers-reduced-motion: reduce)");
  const reducedButtonRule = /\.dashboard-body \.button\s*\{([^}]*)\}/.exec(reducedMotionRule)?.[1] ?? "";
  const reducedPressRule = /\.dashboard-body \.button:not\(:disabled\):hover,\s*\.dashboard-body \.button:not\(:disabled\):active\s*\{([^}]*)\}/.exec(reducedMotionRule)?.[1] ?? "";

  assert.match(buttonRule, /transform 160ms var\(--ease-out\)/);
  assert.match(buttonRule, /background 140ms ease/);
  assert.match(buttonRule, /border-color 140ms ease/);
  assert.match(buttonRule, /color 140ms ease/);
  assert.match(buttonRule, /filter 140ms ease/);
  assert.match(activeRule, /transform:\s*scale\(\.97\)/);
  assert.match(activeRule, /filter:\s*brightness\(\.92\)/);
  assert.doesNotMatch(dashboardCss, /\.dashboard-body \.button:disabled[^}]*transform:/s);
  assert.match(reducedButtonRule, /background 140ms ease/);
  assert.match(reducedButtonRule, /filter 140ms ease/);
  assert.doesNotMatch(reducedButtonRule, /transform 160ms/);
  assert.match(reducedPressRule, /transform:\s*none/);
});

test("dashboard success notices and empty states enter without animating frequent results", () => {
  const dashboardCss = read("rssbot/static/dashboard.css");
  const noticeIndex = dashboardCss.indexOf(".dashboard-body .notice-success,");
  const emptyStateIndex = dashboardCss.indexOf(".dashboard-body .empty-state {", noticeIndex);
  const normalMotionRule = dashboardCss.slice(noticeIndex, dashboardCss.indexOf("@media (prefers-reduced-motion: reduce)", noticeIndex));
  const normalStartingStyle = blockAfter(normalMotionRule, "@starting-style");
  const reducedMotionRule = blockAfter(dashboardCss, "@media (prefers-reduced-motion: reduce)");
  const reducedNoticeRule = blockAfter(reducedMotionRule, ".dashboard-body .notice-success,");
  const reducedStartingStyle = blockAfter(reducedMotionRule, "@starting-style");

  assert.ok(noticeIndex >= 0 && emptyStateIndex > noticeIndex);
  assert.match(normalMotionRule, /opacity 200ms var\(--ease-out\)/);
  assert.match(normalMotionRule, /transform 200ms var\(--ease-out\)/);
  assert.match(normalStartingStyle, /opacity:\s*0/);
  assert.match(normalStartingStyle, /transform:\s*scale\(\.97\)/);
  assert.match(reducedNoticeRule, /opacity 160ms ease/);
  assert.match(reducedNoticeRule, /transform:\s*none/);
  assert.match(reducedStartingStyle, /opacity:\s*0/);
  assert.match(reducedStartingStyle, /transform:\s*none/);
  assert.doesNotMatch(normalMotionRule + reducedMotionRule, /feed-filter-empty/);
  assert.doesNotMatch(normalMotionRule, /\.notice-error|\.notice-warn/);
});

(() => {
  const channelSelects = [...document.querySelectorAll('[data-channel-select]')];
  const channelOutputs = [...document.querySelectorAll('[data-channel-output]')];
  const pendingChannelUpdates = new WeakMap();

  const updateChannel = (value) => {
    const source = channelSelects.find((select) => select.value === value) ?? channelSelects[0];
    if (!source) return;

    for (const select of channelSelects) select.value = source.value;
    const label = source.options[source.selectedIndex]?.textContent?.trim();
    if (!label) return;
    for (const output of channelOutputs) {
      if (output.textContent.trim() === label) continue;
      const previousTimer = pendingChannelUpdates.get(output);
      if (previousTimer !== undefined) clearTimeout(previousTimer);
      output.textContent = label;
      output.classList.add('is-updating');
      const timer = setTimeout(() => {
        output.classList.remove('is-updating');
        pendingChannelUpdates.delete(output);
      }, 80);
      pendingChannelUpdates.set(output, timer);
    }
  };

  for (const select of channelSelects) {
    select.addEventListener('change', () => updateChannel(select.value));
  }
  updateChannel(channelSelects[0]?.value);

  const stage = document.querySelector('[data-shutter]');
  const revealItems = [...document.querySelectorAll('[data-reveal-item]')];
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const groups = new Map();

  for (const item of revealItems) {
    const group = item.parentElement;
    const index = groups.get(group) ?? 0;
    groups.set(group, index + 1);
    item.style.setProperty('--reveal-delay', `${Math.min(index * 70, 280)}ms`);
  }

  if (reduceMotion || !('IntersectionObserver' in window)) {
    stage?.classList.add('is-in');
    for (const item of revealItems) item.classList.add('is-in');
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add('is-in');
      observer.unobserve(entry.target);
    }
  }, { rootMargin: '0px 0px -10% 0px', threshold: 0.08 });

  document.documentElement.classList.add('js');
  if (stage) {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => stage.classList.add('is-in'));
    });
  }
  for (const item of revealItems) observer.observe(item);
})();

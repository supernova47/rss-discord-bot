(() => {
  const panel = document.querySelector("[data-guild-search-panel]");
  const search = document.querySelector("[data-guild-search]");
  const cards = [...document.querySelectorAll("[data-guild-card]")];
  const emptyState = document.querySelector("[data-guild-search-empty]");

  if (!panel || !search || cards.length === 0 || !emptyState) return;
  panel.hidden = false;

  const normalize = (value) => value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase(document.documentElement.lang || undefined)
    .trim();

  search.addEventListener("input", () => {
    const query = normalize(search.value);
    let visibleCount = 0;

    for (const card of cards) {
      const name = card.querySelector("[data-guild-name]")?.textContent || "";
      const matches = normalize(name).includes(query);
      card.hidden = !matches;
      if (matches) visibleCount += 1;
    }

    emptyState.hidden = visibleCount !== 0;
  });
})();

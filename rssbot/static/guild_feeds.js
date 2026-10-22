(function registerFeedFilters(root, createFeedFilters) {
  const feedFilters = createFeedFilters();

  if (typeof module === "object" && module.exports) {
    module.exports = feedFilters;
    return;
  }

  root.FeedListFilters = feedFilters;
  feedFilters.init(root.document);
})(globalThis, function createFeedFilters() {
  function normalize(value) {
    return String(value ?? "").trim().toLocaleLowerCase();
  }

  function matchesFeed(feed, filters) {
    const queryTerms = normalize(filters.query).split(/\s+/u).filter(Boolean);
    const searchText = normalize([feed.title, feed.url, feed.channelName].join(" "));
    const matchesQuery = queryTerms.every((term) => searchText.includes(term));
    const selectedChannel = String(filters.channelId || "all");
    const matchesChannel = selectedChannel === "all" || String(feed.channelId) === selectedChannel;

    let matchesStatus = true;
    if (filters.status === "active") matchesStatus = Boolean(feed.isActive);
    if (filters.status === "paused") matchesStatus = !feed.isActive;
    if (filters.status === "error") matchesStatus = Boolean(feed.hasError);

    return matchesQuery && matchesChannel && matchesStatus;
  }

  function init(document) {
    const filterPanel = document.querySelector("[data-feed-filters]");
    if (!filterPanel) return;

    const searchInput = filterPanel.querySelector("[data-feed-search]");
    const statusSelect = filterPanel.querySelector("[data-feed-status]");
    const channelSelect = filterPanel.querySelector("[data-feed-channel]");
    const resultCount = filterPanel.querySelector("[data-feed-result-count]");
    const resetButton = filterPanel.querySelector("[data-feed-reset]");
    const noResults = document.querySelector("#feed-filter-empty");
    const rows = Array.from(document.querySelectorAll("[data-feed-row]")).map((element) => ({
      element,
      feed: {
        title: element.dataset.feedTitle,
        url: element.dataset.feedUrl,
        channelName: element.dataset.channelName,
        channelId: element.dataset.channelId,
        isActive: element.dataset.active === "true",
        hasError: element.dataset.hasError === "true",
      },
    }));

    if (!searchInput || !statusSelect || !channelSelect || !resultCount || !resetButton || !noResults) return;

    const channelNames = new Map();
    for (const { feed } of rows) {
      if (feed.channelId) channelNames.set(feed.channelId, feed.channelName || "");
    }
    const collator = new Intl.Collator(document.documentElement.lang || undefined, { sensitivity: "base" });
    const channels = Array.from(channelNames, ([id, name]) => ({ id, name })).sort((left, right) =>
      collator.compare(left.name, right.name),
    );
    for (const channel of channels) {
      const option = document.createElement("option");
      option.value = channel.id;
      option.textContent = channel.name || channel.id;
      channelSelect.append(option);
    }

    function updateResults() {
      const filters = {
        query: searchInput.value,
        status: statusSelect.value,
        channelId: channelSelect.value,
      };
      let visibleCount = 0;

      for (const row of rows) {
        const isVisible = matchesFeed(row.feed, filters);
        row.element.hidden = !isVisible;
        if (isVisible) visibleCount += 1;
      }

      const language = document.documentElement.lang;
      resultCount.textContent = language === "en"
        ? `Showing ${visibleCount} of ${rows.length} feeds`
        : `Показано: ${visibleCount} из ${rows.length}`;
      noResults.hidden = visibleCount > 0;
      resetButton.disabled = !filters.query.trim()
        && filters.status === "all"
        && filters.channelId === "all";
    }

    searchInput.addEventListener("input", updateResults);
    statusSelect.addEventListener("change", updateResults);
    channelSelect.addEventListener("change", updateResults);
    resetButton.addEventListener("click", () => {
      searchInput.value = "";
      statusSelect.value = "all";
      channelSelect.value = "all";
      updateResults();
      searchInput.focus();
    });

    updateResults();
  }

  return { init, matchesFeed };
});

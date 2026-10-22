(() => {
  const root = document.getElementById("feed-discovery");
  const trigger = document.getElementById("discover-feed");
  const results = document.getElementById("feed-discovery-results");
  const status = document.getElementById("feed-discovery-status");
  const options = document.getElementById("feed-discovery-options");
  const urlInput = document.querySelector('input[name="url"]');
  const titleInput = document.querySelector('input[name="title"]');
  const csrfInput = document.querySelector('input[name="csrf_token"]');
  if (!root || !trigger || !results || !status || !options || !urlInput || !csrfInput) return;

  const english = document.documentElement.lang === "en";
  const labels = english
    ? {
        find: "Find RSS/Atom feed",
        searching: "Looking for RSS/Atom feeds…",
        none: "No RSS/Atom feed was found. Check the address or paste a direct feed URL.",
        failed: "Could not check this source. Check the URL or try a direct RSS/Atom address.",
        found: (count) => `Found ${count} RSS/Atom feed${count === 1 ? "" : "s"}. Choose one to use.`,
        choose: "Use this feed",
        preview: "Preview latest post",
        selected: "Feed URL selected. Finish the settings and save the feed.",
        previewSelected: "Latest post loaded into the preview. Adjust the settings and save the feed.",
        recent: "Recent entries",
      }
    : {
        find: "Найти RSS/Atom",
        searching: "Ищу RSS/Atom-ленты…",
        none: "RSS/Atom-лента не найдена. Проверьте ссылку или вставьте прямой адрес ленты.",
        failed: "Не удалось проверить источник. Проверьте ссылку или вставьте прямой адрес RSS/Atom.",
        found: (count) => `Найдено лент: ${count}. Выберите нужную.`,
        choose: "Использовать эту ленту",
        preview: "Предпросмотр новости",
        selected: "Адрес ленты выбран. Заполните остальные настройки и сохраните её.",
        previewSelected: "Последняя новость загружена в предпросмотр. Настройте ленту и сохраните её.",
        recent: "Последние записи",
      };
  const englishErrors = new Map([
    [
      "Вставьте ссылку именно на YouTube-канал, например youtube.com/@channel, или прямой Atom-адрес канала.",
      "Paste a YouTube channel URL, such as youtube.com/@channel, or its direct Atom feed URL.",
    ],
    [
      "Не удалось определить ID YouTube-канала. Вставьте ссылку вида /channel/UC… или прямой Atom-адрес канала.",
      "Could not find the YouTube channel ID. Paste a /channel/UC… URL or the channel's direct Atom feed URL.",
    ],
    [
      "YouTube не вернул ожидаемую Atom-ленту для этого канала",
      "YouTube did not return an Atom feed for this channel.",
    ],
  ]);

  trigger.addEventListener("click", async () => {
    const sourceUrl = urlInput.value.trim();
    if (!sourceUrl) {
      urlInput.focus();
      return;
    }

    trigger.disabled = true;
    trigger.textContent = labels.searching;
    results.hidden = false;
    status.textContent = labels.searching;
    options.replaceChildren();
    try {
      const body = new URLSearchParams({ csrf_token: csrfInput.value, url: sourceUrl });
      const response = await fetch(root.dataset.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded", Accept: "application/json" },
        body,
        credentials: "same-origin",
      });
      const data = await response.json();
      if (!response.ok) {
        status.textContent = english ? englishErrors.get(data.error) || labels.failed : data.error || labels.failed;
        return;
      }
      const candidates = Array.isArray(data.candidates) ? data.candidates : [];
      if (!candidates.length) {
        status.textContent = labels.none;
        return;
      }
      status.textContent = labels.found(candidates.length);
      for (const [index, candidate] of candidates.entries()) {
        const card = document.createElement("article");
        card.className = "feed-discovery-option";
        const staggerIndex = Math.min(index, 4);
        card.style.setProperty("--feed-stagger", (staggerIndex * 50) + "ms");
        const copy = document.createElement("div");
        copy.className = "feed-discovery-copy";
        const heading = document.createElement("strong");
        heading.textContent = candidate.title || candidate.url;
        const source = document.createElement("span");
        source.textContent = `${candidate.kind || "RSS/Atom"} · ${candidate.url || ""}`;
        copy.append(heading, source);
        if (Array.isArray(candidate.entries) && candidate.entries.length) {
          const entries = document.createElement("small");
          entries.textContent = `${labels.recent}: ${candidate.entries.join(" · ")}`;
          copy.append(entries);
        }
        const actions = document.createElement("div");
        actions.className = "feed-discovery-actions";
        const selectCandidate = (withPreview) => {
          urlInput.value = candidate.url || "";
          if (titleInput && !titleInput.value.trim()) titleInput.value = candidate.title || "";
          status.textContent = withPreview ? labels.previewSelected : labels.selected;
          urlInput.dispatchEvent(new Event("input", { bubbles: true }));
          if (!withPreview || !candidate.preview_entry) {
            window.dispatchEvent(new CustomEvent("feedflow:clear-preview"));
            return;
          }

          const advancedSettings = document.querySelector(".advanced-settings");
          if (advancedSettings) advancedSettings.open = true;
          window.dispatchEvent(new CustomEvent("feedflow:preview-entry", { detail: candidate.preview_entry }));
          document.querySelector(".preview-wrap")?.scrollIntoView({ behavior: "smooth", block: "center" });
        };
        const select = document.createElement("button");
        select.type = "button";
        select.className = "button button-quiet button-small";
        select.textContent = labels.choose;
        select.addEventListener("click", () => selectCandidate(false));
        const preview = document.createElement("button");
        preview.type = "button";
        preview.className = "button button-primary button-small";
        preview.textContent = labels.preview;
        preview.disabled = !candidate.preview_entry;
        preview.addEventListener("click", () => selectCandidate(true));
        actions.append(select, preview);
        card.append(copy, actions);
        options.append(card);
      }
    } catch {
      status.textContent = labels.failed;
    } finally {
      trigger.disabled = false;
      trigger.textContent = labels.find;
    }
  });
})();

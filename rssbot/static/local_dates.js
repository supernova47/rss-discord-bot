(() => {
  // Keep the server-rendered UTC value as a fallback if browser localization fails.
  const locale = document.documentElement.lang || navigator.languages?.[0] || navigator.language;
  for (const element of document.querySelectorAll("time.local-datetime[data-unix]")) {
    const timestamp = Number(element.dataset.unix);
    if (!Number.isFinite(timestamp)) continue;
    try {
      element.textContent = new Intl.DateTimeFormat(locale, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(timestamp * 1000));
    } catch {
      // Keep the UTC value rendered by the server.
    }
  }
})();

(() => {
  const form = document.querySelector(".settings-form");
  if (!form) return;

  const isEnglish = document.documentElement.lang === "en";
  const feedPlaceholder = isEnglish ? "Feed name" : "Название ленты";
  const sample = {
    title: isEnglish ? "Example news headline" : "Пример заголовка новости",
    url: "https://example.com/news",
    link: "https://example.com/news",
    description: isEnglish ? "A short article summary will appear here. Place it anywhere in your template." : "Краткое описание статьи появится здесь. Его можно разместить в любом месте шаблона.",
    content: isEnglish ? "A short article summary will appear here. Place it anywhere in your template." : "Краткое описание статьи появится здесь. Его можно разместить в любом месте шаблона.",
    author: isEnglish ? "Editorial team" : "Редакция сайта",
    published: "2026-10-21 12:00 UTC",
    published_at: null,
    feed: feedPlaceholder,
    image: "https://example.com/image.jpg",
    media: "https://example.com/animation.gif",
    media_type: "image/gif",
    id: "article-id",
  };
  const defaultSample = { ...sample };
  const samplePublished = new Date("2026-10-20T19:57:00Z");
  const locale = isEnglish ? "en" : "ru";
  const relativeFormatter = new Intl.RelativeTimeFormat(locale, { numeric: "always" });
  const localDateFormatter = new Intl.DateTimeFormat(locale, { dateStyle: "long", timeStyle: "short" });
  const fullDateFormatter = new Intl.DateTimeFormat(locale, {
    weekday: "long", day: "numeric", month: "long", year: "numeric", hour: "numeric", minute: "2-digit",
  });
  const relativeTime = new Intl.RelativeTimeFormat(locale, { numeric: "always" }).format(-3, "hour");
  const localDateTime = localDateFormatter.format(samplePublished);
  const fullDateTime = fullDateFormatter.format(samplePublished);
  let selectedEntry = false;
  let renderedMediaKey = "";
  const fields = (name) => form.querySelector(`[name="${name}"]`);
  const layoutEditor = document.getElementById("layout-order-editor");
  const layoutField = fields("layout_order");
  const layoutBlocks = ["title", "media", "description", "buttons"];
  const separatorBlock = "separator";
  const maxSeparators = layoutBlocks.length;
  const defaultLayoutOrder = layoutBlocks.join(",");
  const linkButtonList = document.getElementById("link-button-list");
  const addLinkButton = document.getElementById("add-link-button");
  const linkButtonsEmpty = document.getElementById("link-buttons-empty");
  const previewLinkButtons = document.getElementById("preview-link-buttons");
  const previewImageNote = document.getElementById("preview-image-note");
  const previewImageMessage = document.getElementById("preview-image-message");
  const previewImage = document.getElementById("preview-image");
  const previewVideo = document.getElementById("preview-video");
  const mediaProxyEndpoint = document.getElementById("feed-discovery")?.dataset.mediaEndpoint || "";
  const replaceTags = (text) => (text || "").replace(/\{([A-Za-z_][A-Za-z0-9_]*)\}/g, (_, key) => sample[key] || "");
  const safeHttpUrl = (value) => {
    try {
      const url = new URL(String(value || ""));
      return url.protocol === "http:" || url.protocol === "https:" ? url.href : "";
    } catch {
      return "";
    }
  };
  const previewMediaUrl = (value) => {
    const sourceUrl = safeHttpUrl(value);
    if (!sourceUrl || !mediaProxyEndpoint) return "";
    const proxyUrl = new URL(mediaProxyEndpoint, window.location.href);
    proxyUrl.searchParams.set("url", sourceUrl);
    return proxyUrl.href;
  };
  const timestampExamplesFor = (timestamp) => {
    const date = new Date(timestamp * 1000);
    if (!Number.isFinite(date.getTime())) return null;
    const difference = (date.getTime() - Date.now()) / 1000;
    const magnitude = Math.abs(difference);
    const units = [
      [31536000, "year"], [2592000, "month"], [604800, "week"],
      [86400, "day"], [3600, "hour"], [60, "minute"], [1, "second"],
    ];
    const [secondsPerUnit, unit] = units.find(([seconds]) => magnitude >= seconds) || units[units.length - 1];
    const relative = relativeFormatter.format(Math.round(difference / secondsPerUnit), unit);
    const local = localDateFormatter.format(date);
    const full = fullDateFormatter.format(date);
    return { relative, localized: local, full, both: `${relative} · ${local}` };
  };
  const escapeHtml = (text) => String(text).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
  const renderDiscordMarkdown = (source) => {
    const protectedHtml = [];
    const token = (html) => {
      const placeholder = `\uE000${protectedHtml.length}\uE001`;
      protectedHtml.push(html);
      return placeholder;
    };
    const makeLink = (label, rawUrl) => {
      try {
        const parsed = new URL(rawUrl);
        if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return null;
        return token(`<a href="${escapeHtml(parsed.href)}" target="_blank" rel="noreferrer">${label}</a>`);
      } catch {
        return null;
      }
    };
    const renderInline = (rawText) => {
      let text = String(rawText);
      text = text.replace(/`([^`\n]+)`/g, (_, code) => token(`<code>${escapeHtml(code)}</code>`));
      text = text.replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g, (match, label, url) => {
        const linked = makeLink(escapeHtml(label), url);
        return linked || match;
      });
      text = text.replace(/https?:\/\/[^\s<]+/g, (match) => {
        const trailing = (match.match(/[.,!?;:)\]]+$/) || [""])[0];
        const url = trailing ? match.slice(0, -trailing.length) : match;
        if (!url) return match;
        const linked = makeLink(escapeHtml(url), url);
        return linked ? linked + trailing : match;
      });
      text = escapeHtml(text);
      text = text
        .replace(/\*\*\*([^\n]+?)\*\*\*/g, "<strong><em>$1</em></strong>")
        .replace(/\*\*([^\n]+?)\*\*/g, "<strong>$1</strong>")
        .replace(/__([^\n]+?)__/g, "<u>$1</u>")
        .replace(/~~([^\n]+?)~~/g, "<s>$1</s>")
        .replace(/\|\|([^\n]+?)\|\|/g, '<span class="markdown-spoiler">$1</span>')
        .replace(/(^|[^\\])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>")
        .replace(/(^|[^\\\w])_([^_\n]+)_(?!\w)/g, "$1<em>$2</em>");
      return text.replace(/\uE000(\d+)\uE001/g, (_, index) => protectedHtml[Number(index)] || "");
    };

    const lines = String(source || "").replace(/\r\n?/g, "\n").split("\n");
    const blocks = [];
    let paragraph = [];
    const flushParagraph = () => {
      if (!paragraph.length) return;
      blocks.push(`<p>${paragraph.map(renderInline).join("<br>")}</p>`);
      paragraph = [];
    };
    for (let index = 0; index < lines.length;) {
      const line = lines[index];
      if (/^\s*```/.test(line)) {
        flushParagraph();
        index += 1;
        const codeLines = [];
        while (index < lines.length && !/^\s*```/.test(lines[index])) codeLines.push(lines[index++]);
        if (index < lines.length) index += 1;
        blocks.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        continue;
      }
      if (!line.trim()) {
        flushParagraph();
        index += 1;
        continue;
      }
      if (/^\s*>\s?/.test(line)) {
        flushParagraph();
        const quoteLines = [];
        while (index < lines.length && /^\s*>\s?/.test(lines[index])) {
          quoteLines.push(lines[index++].replace(/^\s*>\s?/, ""));
        }
        blocks.push(`<blockquote>${quoteLines.map(renderInline).join("<br>")}</blockquote>`);
        continue;
      }
      const unordered = line.match(/^\s*[-*+]\s+(.+)$/);
      const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
      if (unordered || ordered) {
        flushParagraph();
        const listItems = [];
        const listPattern = unordered ? /^\s*[-*+]\s+(.+)$/ : /^\s*\d+[.)]\s+(.+)$/;
        while (index < lines.length) {
          const match = lines[index].match(listPattern);
          if (!match) break;
          listItems.push(`<li>${renderInline(match[1])}</li>`);
          index += 1;
        }
        const tagName = unordered ? "ul" : "ol";
        blocks.push(`<${tagName}>${listItems.join("")}</${tagName}>`);
        continue;
      }
      const heading = line.match(/^\s*(#{1,3})\s+(.+)$/);
      if (heading) {
        flushParagraph();
        const level = heading[1].length;
        blocks.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
        index += 1;
        continue;
      }
      paragraph.push(line);
      index += 1;
    }
    flushParagraph();
    return blocks.join("");
  };
  const setText = (id, value) => {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  };
  const orderedLayoutItems = () => Array.from(layoutEditor?.querySelectorAll("[data-layout-block]") || []);
  const isValidLayoutOrder = (order) => {
    const content = order.filter((item) => item !== separatorBlock);
    return content.length === layoutBlocks.length
      && new Set(content).size === layoutBlocks.length
      && layoutBlocks.every((block) => content.includes(block))
      && order.every((item) => layoutBlocks.includes(item) || item === separatorBlock)
      && order.filter((item) => item === separatorBlock).length <= maxSeparators
      && order[0] !== separatorBlock
      && !order.some((item, index) => item === separatorBlock && order[index - 1] === separatorBlock);
  };
  const updateLayoutField = () => {
    const items = orderedLayoutItems();
    if (layoutField) layoutField.value = items.map((item) => item.dataset.layoutBlock).join(",");
    const separatorCount = items.filter((item) => item.dataset.layoutBlock === separatorBlock).length;
    items.forEach((item, index) => {
      item.querySelector('[data-move="up"]').disabled = index === 0
        || (item.dataset.layoutBlock === separatorBlock && index === 1);
      item.querySelector('[data-move="down"]').disabled = index === items.length - 1
        || (index === 0 && item.nextElementSibling?.dataset.layoutBlock === separatorBlock);
      const insert = item.querySelector("[data-insert-separator]");
      if (insert) {
        insert.disabled = separatorCount >= maxSeparators || item.nextElementSibling?.dataset.layoutBlock === separatorBlock;
      }
    });
  };
  const createSeparatorItem = () => {
    const item = document.createElement("li");
    item.dataset.layoutBlock = separatorBlock;
    const label = document.createElement("span");
    label.textContent = isEnglish ? "Separator" : "Разделитель";
    const actions = document.createElement("div");
    for (const [action, text, ariaLabel] of [
      ["up", "↑", isEnglish ? "Move up" : "Переместить вверх"],
      ["down", "↓", isEnglish ? "Move down" : "Переместить вниз"],
    ]) {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.move = action;
      button.setAttribute("aria-label", ariaLabel);
      button.textContent = text;
      actions.append(button);
    }
    const remove = document.createElement("button");
    remove.type = "button";
    remove.dataset.removeSeparator = "";
    remove.setAttribute("aria-label", isEnglish ? "Remove separator" : "Удалить разделитель");
    remove.textContent = "×";
    actions.append(remove);
    item.append(label, actions);
    return item;
  };
  const createLinkButtonRow = (labelValue = "", urlValue = "") => {
    const row = document.createElement("div");
    row.className = "link-button-row";
    const makeField = (caption, name, value, placeholder, maxLength) => {
      const field = document.createElement("label");
      field.className = "field";
      const title = document.createElement("span");
      title.textContent = caption;
      const input = document.createElement("input");
      input.type = "text";
      input.name = name;
      input.value = value;
      input.placeholder = placeholder;
      input.maxLength = maxLength;
      if (name === "button_urls") input.inputMode = "url";
      field.append(title, input);
      return field;
    };
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "button button-quiet button-small";
    remove.dataset.removeLinkButton = "";
    remove.textContent = isEnglish ? "Remove" : "Убрать";
    row.append(
      makeField(isEnglish ? "Button label" : "Подпись", "button_labels", labelValue, isEnglish ? "Read article" : "Читать новость", 80),
      makeField(isEnglish ? "Link" : "Ссылка", "button_urls", urlValue, "{url}", 512),
      remove,
    );
    return row;
  };
  const buttonRows = () => Array.from(linkButtonList?.querySelectorAll(".link-button-row") || []);
  const updateButtonEditor = () => {
    const rows = buttonRows();
    if (linkButtonsEmpty) linkButtonsEmpty.hidden = rows.length > 0;
    if (addLinkButton) addLinkButton.disabled = rows.length >= 5;
    if (!previewLinkButtons) return [];
    previewLinkButtons.replaceChildren();
    for (const row of rows) {
      const label = row.querySelector('[name="button_labels"]').value.trim();
      const url = row.querySelector('[name="button_urls"]').value.trim();
      if (!label && !url) continue;
      const button = document.createElement("span");
      button.className = "preview-link-button";
      button.textContent = label || (isEnglish ? "Link button" : "Кнопка-ссылка");
      previewLinkButtons.append(button);
    }
    previewLinkButtons.hidden = previewLinkButtons.childElementCount === 0;
    return Array.from(previewLinkButtons.children);
  };

  if (layoutEditor && layoutField) {
    const savedOrder = layoutField.value.split(",").map((item) => item.trim()).filter(Boolean);
    if (isValidLayoutOrder(savedOrder)) {
      const items = new Map(orderedLayoutItems().map((item) => [item.dataset.layoutBlock, item]));
      layoutEditor.replaceChildren(...savedOrder.map((block) => block === separatorBlock ? createSeparatorItem() : items.get(block)));
    } else {
      layoutField.value = defaultLayoutOrder;
    }
    layoutEditor.addEventListener("click", (event) => {
      const remove = event.target.closest("[data-remove-separator]");
      if (remove) {
        remove.closest("[data-layout-block]").remove();
        updateLayoutField();
        update();
        return;
      }
      const insert = event.target.closest("[data-insert-separator]");
      if (insert && !insert.disabled) {
        const item = insert.closest("[data-layout-block]");
        layoutEditor.insertBefore(createSeparatorItem(), item.nextElementSibling);
        updateLayoutField();
        update();
        return;
      }
      const button = event.target.closest("[data-move]");
      const item = button?.closest("[data-layout-block]");
      if (!button || !item) return;
      if (button.dataset.move === "up" && item.previousElementSibling) {
        layoutEditor.insertBefore(item, item.previousElementSibling);
      } else if (button.dataset.move === "down" && item.nextElementSibling) {
        layoutEditor.insertBefore(item.nextElementSibling, item);
      }
      updateLayoutField();
      update();
    });
    updateLayoutField();
  }

  if (linkButtonList && addLinkButton) {
    addLinkButton.addEventListener("click", () => {
      if (buttonRows().length >= 5) return;
      linkButtonList.append(createLinkButtonRow(
        isEnglish ? "Read article" : "Читать новость",
        "{url}",
      ));
      updateButtonEditor();
      update();
    });
    linkButtonList.addEventListener("click", (event) => {
      if (!event.target.closest("[data-remove-link-button]")) return;
      event.target.closest(".link-button-row").remove();
      updateButtonEditor();
      update();
    });
  }

  const update = () => {
    const name = fields("display_name")?.value.trim() || (isEnglish ? "News" : "Новости");
    sample.feed = fields("title")?.value.trim() || feedPlaceholder;
    const avatarUrl = fields("avatar_url")?.value.trim() || "";
    const avatar = document.getElementById("preview-avatar");
    avatar.replaceChildren();
    const file = fields("avatar_file")?.files?.[0];
    const renderAvatar = (url) => {
      if (!url) { avatar.textContent = "◔"; return; }
      const image = document.createElement("img");
      image.src = url;
      image.alt = "";
      image.referrerPolicy = "no-referrer";
      image.onerror = () => { avatar.textContent = "◔"; };
      avatar.append(image);
    };
    if (file) {
      renderAvatar(URL.createObjectURL(file));
    } else if (fields("clear_avatar")?.checked) {
      avatar.textContent = "◔";
    } else if (avatarUrl.startsWith("https://")) {
      renderAvatar(avatarUrl);
    } else {
      const current = document.querySelector(".avatar-current img");
      renderAvatar(current?.src || "");
    }

    const content = replaceTags(fields("message_template")?.value);
    const title = replaceTags(fields("embed_title_template")?.value);
    const description = replaceTags(fields("embed_description_template")?.value);
    setText("preview-name", name.slice(0, 32));
    document.getElementById("preview-message").innerHTML = renderDiscordMarkdown(content);
    document.getElementById("preview-title").innerHTML = renderDiscordMarkdown(title);
    document.getElementById("preview-description").innerHTML = renderDiscordMarkdown(description);
    const timestampStyle = fields("timestamp_style")?.value || "both";
    const timestampExamples = {
      relative: relativeTime,
      localized: localDateTime,
      full: fullDateTime,
      both: `${relativeTime} · ${localDateTime}`,
    };
    const hasPublishedAt = sample.published_at !== null && sample.published_at !== "";
    const publishedAt = Number(sample.published_at);
    const entryTimestampExamples = hasPublishedAt && Number.isFinite(publishedAt) ? timestampExamplesFor(publishedAt) : null;
    const activeTimestampExamples = entryTimestampExamples || (selectedEntry
      ? { relative: "", localized: "", full: "", both: "" }
      : timestampExamples);
    const footerTimestamp = activeTimestampExamples[timestampStyle] || activeTimestampExamples.both;
    setText("preview-footer", `${sample.feed}${footerTimestamp ? ` · ${footerTimestamp}` : ""}`);

    const color = fields("embed_color")?.value || "#5865F2";
    const card = document.getElementById("preview-embed");
    card.style.borderLeftColor = color;
    const showImage = Boolean(fields("show_image")?.checked);
    const mediaUrl = selectedEntry ? previewMediaUrl(sample.media || sample.image) : "";
    const isVideo = String(sample.media_type || "").toLowerCase().startsWith("video/");
    const mediaKey = `${showImage}|${selectedEntry}|${mediaUrl}|${isVideo}`;
    previewImage.onerror = () => {
      previewImage.hidden = true;
      previewImageMessage.hidden = false;
      previewImageMessage.textContent = isEnglish ? "Could not load this image." : "Не удалось загрузить изображение.";
      previewImageNote.classList.remove("has-media");
    };
    previewVideo.onerror = () => {
      previewVideo.hidden = true;
      previewImageMessage.hidden = false;
      previewImageMessage.textContent = isEnglish ? "Could not load this video." : "Не удалось загрузить видео.";
      previewImageNote.classList.remove("has-media");
    };
    if (mediaKey !== renderedMediaKey) {
      renderedMediaKey = mediaKey;
      previewImage.hidden = true;
      previewVideo.hidden = true;
      previewImage.removeAttribute("src");
      previewVideo.pause();
      previewVideo.removeAttribute("src");
      previewVideo.load();
      previewImageNote.classList.remove("has-media");
      previewImageMessage.hidden = false;
      previewImageMessage.textContent = selectedEntry
        ? (isEnglish ? "This entry has no image or video." : "В этой записи нет изображения или видео.")
        : (isEnglish ? "Media appears here when the feed includes it." : "Здесь появится медиа, если оно есть в RSS-ленте.");
      previewImageNote.hidden = !showImage;

      if (showImage && mediaUrl) {
        previewImageMessage.hidden = true;
        previewImageNote.classList.add("has-media");
        if (isVideo) {
          previewVideo.src = mediaUrl;
          previewVideo.hidden = false;
        } else {
          previewImage.src = mediaUrl;
          previewImage.hidden = false;
        }
      }
    }
    const previewButtons = updateButtonEditor();
    const blocks = {
      title: document.getElementById("preview-title"),
      media: previewImageNote,
      description: document.getElementById("preview-description"),
      buttons: previewLinkButtons,
    };
    const visible = {
      title: Boolean(title),
      media: showImage,
      description: Boolean(description),
      buttons: previewButtons.length > 0,
    };
    const order = (layoutField?.value || defaultLayoutOrder).split(",");
    const previewChildren = [];
    for (const block of order) {
      if (block === separatorBlock) {
        const previousChild = previewChildren[previewChildren.length - 1];
        if (previousChild && !previousChild.classList.contains("preview-separator")) {
          const separator = document.createElement("div");
          separator.className = "preview-separator";
          previewChildren.push(separator);
        }
        continue;
      }
      if (blocks[block] && visible[block]) previewChildren.push(blocks[block]);
    }
    const footer = document.getElementById("preview-footer");
    previewChildren.push(footer);
    card.replaceChildren(...previewChildren);
    card.hidden = !title && !description && !showImage && previewButtons.length === 0;
  };

  window.addEventListener("feedflow:clear-preview", () => {
    Object.assign(sample, defaultSample);
    selectedEntry = false;
    update();
  });
  window.addEventListener("feedflow:preview-entry", (event) => {
    const entry = event.detail;
    if (!entry || typeof entry !== "object") return;
    const text = (value, limit) => String(value || "").slice(0, limit);
    sample.title = text(entry.title, 300) || (isEnglish ? "Untitled entry" : "Без заголовка");
    sample.url = safeHttpUrl(entry.url);
    sample.link = sample.url;
    sample.description = text(entry.description, 1500);
    sample.content = sample.description;
    sample.author = text(entry.author, 150);
    sample.id = text(entry.key, 256);
    sample.image = safeHttpUrl(entry.image);
    sample.media = safeHttpUrl(entry.media);
    sample.media_type = text(entry.media_type, 100).toLowerCase();
    const publishedAt = Number(entry.published_at);
    if (entry.published_at !== null && entry.published_at !== "" && Number.isFinite(publishedAt)) {
      sample.published_at = publishedAt;
      const publishedDate = new Date(publishedAt * 1000);
      sample.published = Number.isFinite(publishedDate.getTime())
        ? `${publishedDate.toISOString().slice(0, 16).replace("T", " ")} UTC`
        : "";
    } else {
      sample.published_at = null;
      sample.published = "";
    }
    selectedEntry = true;
    update();
  });
  form.addEventListener("input", update);
  form.addEventListener("change", update);
  update();
})();


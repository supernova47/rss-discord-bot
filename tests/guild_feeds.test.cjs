const assert = require("node:assert/strict");
const test = require("node:test");

let matchesFeed;
try {
  ({ matchesFeed } = require("../rssbot/static/guild_feeds.js"));
} catch {
  // Keep the first run as an assertion failure until the feature module exists.
}

function requireMatcher() {
  assert.equal(typeof matchesFeed, "function", "guild feed filters should export matchesFeed");
  return matchesFeed;
}

const activeFeed = {
  title: "Новости FeedFlow",
  url: "https://example.com/news.xml",
  channelName: "Новости",
  channelId: "123",
  isActive: true,
  hasError: false,
};

test("search matches feed title, URL, and Discord channel without case sensitivity", () => {
  const matcher = requireMatcher();

  for (const query of ["FEEDFLOW", "NEWS.XML", "НОВОСТИ"]) {
    assert.equal(matcher(activeFeed, { query, status: "all", channelId: "all" }), true);
  }
  assert.equal(matcher(activeFeed, { query: "gaming", status: "all", channelId: "all" }), false);
});

test("status filters include active and paused feeds while error filter includes either state", () => {
  const matcher = requireMatcher();
  const pausedFeed = { ...activeFeed, isActive: false };
  const activeErrorFeed = { ...activeFeed, hasError: true };
  const pausedErrorFeed = { ...pausedFeed, hasError: true };

  assert.equal(matcher(activeFeed, { query: "", status: "active", channelId: "all" }), true);
  assert.equal(matcher(pausedFeed, { query: "", status: "active", channelId: "all" }), false);
  assert.equal(matcher(pausedFeed, { query: "", status: "paused", channelId: "all" }), true);
  assert.equal(matcher(activeErrorFeed, { query: "", status: "error", channelId: "all" }), true);
  assert.equal(matcher(pausedErrorFeed, { query: "", status: "error", channelId: "all" }), true);
  assert.equal(matcher(activeFeed, { query: "", status: "error", channelId: "all" }), false);
});

test("channel and search filters apply together", () => {
  const matcher = requireMatcher();

  assert.equal(matcher(activeFeed, { query: "news", status: "all", channelId: "123" }), true);
  assert.equal(matcher(activeFeed, { query: "news", status: "all", channelId: "456" }), false);
});

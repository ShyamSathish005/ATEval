import test from "node:test";
import assert from "node:assert/strict";
import config from "../vite.config.mjs";

function proxyConfiguration(proxy) {
  let configure;
  proxy["/api"].configure({ on(event, callback) { assert.equal(event, "proxyReq"); configure = callback; } });
  const removed = [];
  configure({ removeHeader(name) { removed.push(name); } });
  return removed;
}

test("development API uses a relative same-origin proxy and strips browser Origin upstream", () => {
  assert.equal(config.server.proxy["/api"].target, process.env.ATEVAL_API_ORIGIN ?? "http://127.0.0.1:8000");
  assert.deepEqual(proxyConfiguration(config.server.proxy), ["origin"]);
});

test("production preview API uses the local backend proxy instead of a development URL in the client", () => {
  assert.equal(config.preview.proxy["/api"].target, process.env.ATEVAL_API_ORIGIN ?? "http://127.0.0.1:8000");
  assert.deepEqual(proxyConfiguration(config.preview.proxy), ["origin"]);
});

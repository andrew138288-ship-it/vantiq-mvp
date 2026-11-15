import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const extensionRoot = resolve(here, "..");
const manifest = JSON.parse(readFileSync(resolve(extensionRoot, "manifest.json"), "utf8"));

test("extension uses Manifest V3 and declares its entry points", () => {
  assert.equal(manifest.manifest_version, 3);
  assert.equal(manifest.background.service_worker, "service-worker.js");
  assert.equal(manifest.side_panel.default_path, "sidepanel.html");
  for (const file of [
    "content.js",
    "service-worker.js",
    "sidepanel.html",
    "sidepanel.css",
    "sidepanel.js",
    "transcript.mjs",
  ]) {
    assert.ok(existsSync(resolve(extensionRoot, file)), `missing ${file}`);
  }
});

test("permissions remain narrow and WhatsApp-only for page access", () => {
  assert.deepEqual([...manifest.permissions].sort(), ["activeTab", "sidePanel", "storage"]);
  assert.deepEqual(manifest.content_scripts[0].matches, ["https://web.whatsapp.com/*"]);
  assert.ok(manifest.host_permissions.includes("https://web.whatsapp.com/*"));
  assert.ok(!manifest.host_permissions.includes("<all_urls>"));
});

test("extension has no automatic message-sending permission or content script injection elsewhere", () => {
  assert.ok(!manifest.permissions.includes("scripting"));
  assert.ok(!manifest.permissions.includes("debugger"));
  assert.deepEqual(manifest.content_scripts[0].matches, ["https://web.whatsapp.com/*"]);
});

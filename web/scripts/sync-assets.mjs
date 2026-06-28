// Copy the shared, committed data + media from the desktop app's assets/ folder
// into web/public/ so the web app serves them. Vercel builds with this directory
// as the root, so the copied files (committed) are what gets deployed.
//
//   node scripts/sync-assets.mjs
//
// Re-run after regenerating any dataset in ../assets.

import { cpSync, mkdirSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const assets = resolve(here, "..", "..", "assets");
const publicDir = resolve(here, "..", "public");

if (!existsSync(assets)) {
  console.error(`Source assets not found at ${assets}`);
  process.exit(1);
}

// (source under assets/, destination under public/)
const items = [
  ["data", "data"],
  ["sprites", "sprites"],
  ["items", "items"],
  ["types", "types"],
  ["categories", "categories"],
  ["sounds", "sounds"],
];

for (const [src, dst] of items) {
  const from = resolve(assets, src);
  const to = resolve(publicDir, dst);
  if (!existsSync(from)) {
    console.warn(`skip (missing): ${from}`);
    continue;
  }
  mkdirSync(to, { recursive: true });
  cpSync(from, to, { recursive: true });
  console.log(`synced ${src} -> public/${dst}`);
}

console.log("Asset sync complete.");

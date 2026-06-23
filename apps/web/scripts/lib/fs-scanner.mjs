import { readdirSync, statSync } from "node:fs";
import { resolve } from "node:path";

export function walkFiles(root, options = {}) {
  const {
    extensions,
    skipDirectories = ["node_modules", "dist"],
    skipDotDirectories = true,
  } = options;

  const acceptedExtensions = extensions ? new Set(extensions) : null;
  const files = [];

  function walk(dir) {
    for (const entry of readdirSync(dir)) {
      if (skipDirectories.includes(entry)) {
        continue;
      }
      if (skipDotDirectories && entry.startsWith(".")) {
        continue;
      }

      const fullPath = resolve(dir, entry);
      const stats = statSync(fullPath);
      if (stats.isDirectory()) {
        walk(fullPath);
        continue;
      }

      if (!acceptedExtensions) {
        files.push(fullPath);
        continue;
      }

      const ext = entry.includes(".") ? entry.slice(entry.lastIndexOf(".")) : "";
      if (acceptedExtensions.has(ext)) {
        files.push(fullPath);
      }
    }
  }

  walk(root);
  return files;
}
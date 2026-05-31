import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const failures = [];
const files = await collect(join(root, "app"), join(root, "components"));

for (const file of files.filter((item) => item.endsWith(".tsx"))) {
  if (file.endsWith("SubmitButton.tsx")) {
    continue;
  }
  const source = await readFile(file, "utf8");
  if (/console\.(log|warn|error)\s*\(/.test(source)) {
    failures.push(`${short(file)} contains console-only interaction code.`);
  }
  if (/coming soon/i.test(source)) {
    failures.push(`${short(file)} contains "coming soon" copy.`);
  }
  for (const match of source.matchAll(/<button\b([^>]*)>/g)) {
    const attrs = match[1];
    const before = source.slice(Math.max(0, match.index - 180), match.index);
    const actionable =
      attrs.includes("type=\"button\"") ||
      attrs.includes("onClick=") ||
      before.includes("<form") ||
      source.slice(match.index, match.index + 220).includes("</SubmitButton>");
    if (!actionable) {
      failures.push(`${short(file)} has a button without form, onClick, or type="button".`);
    }
  }
  for (const match of source.matchAll(/<a\b([^>]*)>/g)) {
    const attrs = match[1];
    if (!attrs.includes("href=")) {
      failures.push(`${short(file)} has an anchor without href.`);
    }
    if (/href=["']#["']/.test(attrs)) {
      failures.push(`${short(file)} has a placeholder # link.`);
    }
  }
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(`Button smoke test passed for ${files.length} TSX files.`);

async function collect(...paths) {
  const out = [];
  for (const path of paths) {
    for (const entry of await readdir(path, { withFileTypes: true })) {
      const full = join(path, entry.name);
      if (entry.isDirectory()) {
        out.push(...(await collect(full)));
      } else {
        out.push(full);
      }
    }
  }
  return out;
}

function short(file) {
  return file.replace(root, "");
}

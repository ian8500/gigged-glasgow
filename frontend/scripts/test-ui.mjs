import { access } from "node:fs/promises";
import { join } from "node:path";
import { spawn } from "node:child_process";

const root = new URL("..", import.meta.url).pathname;
const routes = ["/", "/venues", "/scrape", "/events", "/events/new", "/weekly", "/social", "/settings"];
const failures = [];

for (const route of routes) {
  const pagePath = route === "/" ? join(root, "app", "page.tsx") : join(root, "app", route.slice(1), "page.tsx");
  try {
    await access(pagePath);
    console.log(`PASS route exists ${route}`);
  } catch {
    failures.push(`FAIL route missing ${route} (${pagePath})`);
  }
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

await runNextBuild();
console.log("PASS UI smoke build completed for required routes.");

function runNextBuild() {
  return new Promise((resolve, reject) => {
    const bin = join(root, "node_modules", ".bin", "next");
    const child = spawn(bin, ["build"], {
      cwd: root,
      stdio: "inherit",
      env: {
        ...process.env,
        NEXT_TELEMETRY_DISABLED: "1"
      }
    });
    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`next build exited with ${code}`));
    });
  });
}

// Playwright webServer command: builds a fresh, dedicated fixture database and
// runs the isolated test API on it. Never reads DATABASE_URL and never touches
// .local/test-data/manual.sqlite3 or any application database.
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../../..");
const dir = path.join(repo, ".local", "e2e");
const db = path.join(dir, "e2e.sqlite3");
const manifest = path.join(dir, "manifest.json");
// E2E_PYTHON lets CI (Linux, no .venv) name its interpreter.
const python = process.env.E2E_PYTHON ?? path.join(repo, "services/api/.venv/Scripts/python.exe");
const port = process.env.E2E_API_PORT ?? "8010";

mkdirSync(dir, { recursive: true });
for (const f of [db, manifest]) if (existsSync(f)) rmSync(f);

const env = {
  ...process.env,
  ENVIRONMENT: "dev",
  TEST_DATA_PASSWORD: process.env.E2E_CUSTOMER_PASSWORD ?? "PriveoE2eFixture123!",
  TEST_DATA_ADMIN_PASSWORD: process.env.E2E_ADMIN_PASSWORD ?? "PriveoE2eAdmin123!",
};
delete env.DATABASE_URL;

const init = spawnSync(python, [
  "scripts/test_data.py", "--database-file", db, "--init", "--refresh", "all", "--output", manifest,
], { cwd: path.join(repo, "services/api"), env, stdio: "inherit" });
if (init.status !== 0) process.exit(init.status ?? 1);

const api = spawn(process.platform === "win32" ? "powershell" : "pwsh", [
  "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
  path.join(repo, "tools/test-data/start-api.ps1"), "-DatabaseFile", db, "-Port", port, "-SerializeRequests",
], { cwd: repo, env, stdio: "inherit" });
api.on("exit", (code) => process.exit(code ?? 0));
process.on("SIGTERM", () => api.kill());

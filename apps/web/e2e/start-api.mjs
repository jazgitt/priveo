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

// start-api.ps1 does the same on Windows and in CI. Where PowerShell is missing
// (a Mac), set the same variables here and run the same serialised API.
const hasPowerShell = process.platform === "win32"
  || spawnSync("pwsh", ["-NoProfile", "-Command", "exit 0"], { stdio: "ignore" }).status === 0;
let api;
if (hasPowerShell) {
  api = spawn(process.platform === "win32" ? "powershell" : "pwsh", [
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
    path.join(repo, "tools/test-data/start-api.ps1"), "-DatabaseFile", db, "-Port", port, "-SerializeRequests",
  ], { cwd: repo, env, stdio: "inherit" });
} else {
  const fixtureEnv = {
    ...env,
    DATABASE_URL: `sqlite:///${db}`,
    ENVIRONMENT: "dev",
    RESEND_API_KEY: " ", // a space: an empty value would let services/api/.env send real email
    TOKEN_SECRET: "local-fixture-only-secret-not-for-deployment",
    MOCK_EMAIL_CODE: "246810",
    MEDIA_ROOT: path.join(dir, "media"),
    MONEY_GST_CONFIGURATION_MOCK: "true",
    MONEY_UPI_ID: "priveo-placeholder@upi",
    MONEY_UPI_PAYEE_NAME: "Priveo (test placeholder)",
    MONEY_UPI_QR_URL: "",
    MONEY_SELLER_NAME: "Priveo (placeholder seller)",
    MONEY_SELLER_ADDRESS: "Placeholder address",
    MONEY_SELLER_GSTIN: "00PLACEHOLDER0Z0",
    MONEY_GST_RATE_PERCENT: "18",
    MONEY_GST_MODE: "CGST_SGST",
  };
  const verify = spawnSync(python, ["scripts/test_data.py", "--database-file", db],
    { cwd: path.join(repo, "services/api"), env: fixtureEnv, stdio: "ignore" });
  if (verify.status !== 0) process.exit(verify.status ?? 1);
  api = spawn(python, [
    "-m", "uvicorn", "serial_app:app", "--app-dir", path.join(repo, "tools/test-data"),
    "--host", "0.0.0.0", "--port", port,
  ], { cwd: path.join(repo, "services/api"), env: fixtureEnv, stdio: "inherit" });
}
api.on("exit", (code) => process.exit(code ?? 0));
process.on("SIGTERM", () => api.kill());

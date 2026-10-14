import { expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const manifestPath = path.resolve(here, "../../../.local/e2e/manifest.json");

export const ADMIN_LOGIN = "priveopapa";
export const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "PriveoE2eAdmin123!";

interface Scenario {
  id: string;
  customer_id: string;
  customer_login: string;
  payment_ids: string[];
  society_id: string;
  as_of: string;
}

/** A seeded scenario from the manifest written when the fixture database was built. */
export function scenario(id: string): Scenario {
  const m = JSON.parse(readFileSync(manifestPath, "utf8")) as { scenarios: Scenario[] };
  const s = m.scenarios.find((x) => x.id === id);
  if (!s) throw new Error(`Scenario ${id} is not in the manifest`);
  return s;
}

export async function signIn(page: Page, login = ADMIN_LOGIN, password = ADMIN_PASSWORD) {
  await page.goto("");
  await page.getByLabel("User ID").fill(login);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

export async function signInAsAdmin(page: Page) {
  await signIn(page);
  await expect(page.getByRole("navigation", { name: "Admin areas" })).toBeVisible();
}

/** An ISO date `days` after `iso` (fixture dates are anchored to the scenario's as_of). */
export function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** The value of the <option> in a select whose text contains `text`. */
export async function optionValue(select: import("@playwright/test").Locator, text: string): Promise<string> {
  const value = await select.locator("option", { hasText: text }).first().getAttribute("value");
  if (!value) throw new Error(`No option containing "${text}"`);
  return value;
}

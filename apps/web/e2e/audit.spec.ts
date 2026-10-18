import { expect, test } from "@playwright/test";
import { signInAsAdmin } from "./helpers";

test.describe("Audit", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
    await page.getByRole("link", { name: "Audit", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Audit" })).toBeVisible();
  });

  test("says it does not refresh by itself, and has a Refresh button", async ({ page }) => {
    await expect(page.getByRole("note")).toContainText("does not update by itself");
    await expect(page.getByRole("note")).toContainText("last 1000 events");
    await expect(page.getByRole("button", { name: "Refresh" })).toBeEnabled();
  });

  test("does not ask the server again until Refresh is pressed", async ({ page }) => {
    await expect(page.getByRole("note")).toContainText("Loaded at");
    let calls = 0;
    page.on("request", (r) => { if (r.url().includes("/directory/audit")) calls += 1; });
    await page.waitForTimeout(1500);
    await page.evaluate(() => window.dispatchEvent(new Event("focus")));
    expect(calls).toBe(0);
    await page.getByRole("button", { name: "Refresh" }).click();
    await expect.poll(() => calls).toBe(1);
  });
});

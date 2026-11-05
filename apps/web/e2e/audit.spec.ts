import { expect, test } from "@playwright/test";
import { signInAsAdmin } from "./helpers";

test.describe("Audit trail", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
    await page.getByRole("link", { name: "Audit trail", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Audit trail" })).toBeVisible();
  });

  test("says it does not refresh by itself, and has a Refresh button [ADM-SET-06]", async ({ page }) => {
    await expect(page.getByRole("note")).toContainText("does not update by itself");
    await expect(page.getByRole("note")).toContainText("apply to every site");
    await expect(page.getByRole("button", { name: "Refresh" })).toBeEnabled();
  });

  test("does not ask the server again until Refresh is pressed [ADM-SET-06]", async ({ page }) => {
    await expect(page.getByRole("note")).toContainText("Loaded at");
    let calls = 0;
    page.on("request", (r) => { if (r.url().includes("/directory/audit")) calls += 1; });
    await page.waitForTimeout(1500);
    await page.evaluate(() => window.dispatchEvent(new Event("focus")));
    expect(calls).toBe(0);
    await page.getByRole("button", { name: "Refresh" }).click();
    await expect.poll(() => calls).toBe(1);
  });

  test("searches only when the button is pressed, from 3 characters [ADM-SET-09]", async ({ page }) => {
    let calls = 0;
    let lastQ: string | null = null;
    page.on("request", (r) => {
      if (r.url().includes("/directory/audit")) { calls += 1; lastQ = new URL(r.url()).searchParams.get("q"); }
    });
    const box = page.getByLabel("Search");
    const button = page.getByRole("button", { name: "Search", exact: true });
    await box.fill("lo");
    await expect(button).toBeDisabled();
    await box.fill("login");
    await page.waitForTimeout(500);
    expect(calls).toBe(0);
    await button.click();
    await expect.poll(() => lastQ).toBe("login");
    await page.getByRole("button", { name: "Clear" }).click();
    await expect(box).toHaveValue("");
  });
});

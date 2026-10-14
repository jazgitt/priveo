import { expect, test } from "@playwright/test";
import { signInAsAdmin } from "./helpers";

test.describe("Settings", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
    await page.getByRole("link", { name: "Settings", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  });

  test("seller identity is read-only", async ({ page }) => {
    await expect(page.getByText(/Seller GSTIN/)).toBeVisible();
    await expect(page.getByLabel(/Seller GSTIN/)).toHaveCount(0);
  });

  test("saves the helpline number and keeps it after a reload", async ({ page }) => {
    const field = page.getByLabel("Helpline number", { exact: true });
    await field.fill("9876543210");
    await page.getByRole("button", { name: "Save Helpline number" }).click();
    await expect(page.getByText("Helpline number saved.")).toBeVisible();

    await page.reload();
    await expect(page.getByLabel("Helpline number", { exact: true })).toHaveValue("9876543210");
  });

  test("rejects an invalid helpline number", async ({ page }) => {
    await page.getByLabel("Helpline number", { exact: true }).fill("abc");
    await page.getByRole("button", { name: "Save Helpline number" }).click();
    await expect(page.getByText("Helpline number saved.")).toHaveCount(0);
    // Nothing invalid was stored: the saved value is still the seeded one.
    await page.reload();
    await expect(page.getByLabel("Helpline number", { exact: true })).not.toHaveValue("abc");
  });
});

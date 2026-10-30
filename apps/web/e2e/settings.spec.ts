import { expect, test } from "@playwright/test";
import { signInAsAdmin } from "./helpers";

test.describe("Settings", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
    await page.getByRole("link", { name: "Settings", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
    // Each section is its own tab.
    await expect(page.getByRole("tablist", { name: "Settings sections" })).toBeVisible();
  });

  test("seller identity can be edited and is kept after a reload [ADM-SET-04]", async ({ page }) => {
    await page.getByRole("tab", { name: "Invoice" }).click();
    const name = page.getByLabel("Seller legal name", { exact: true });
    await name.fill("Priveo Services Pvt Ltd");
    await page.getByRole("button", { name: "Save Seller legal name" }).click();
    await expect(page.getByText("Seller legal name saved.")).toBeVisible();

    await page.reload();
    await page.getByRole("tab", { name: "Invoice" }).click();
    await expect(page.getByLabel("Seller legal name", { exact: true })).toHaveValue("Priveo Services Pvt Ltd");
  });

  test("saves the helpline number and keeps it after a reload [ADM-SET-03]", async ({ page }) => {
    const field = page.getByLabel("Helpline number", { exact: true });
    await field.fill("9876543210");
    await page.getByRole("button", { name: "Save Helpline number" }).click();
    await expect(page.getByText("Helpline number saved.")).toBeVisible();

    await page.reload();
    await expect(page.getByLabel("Helpline number", { exact: true })).toHaveValue("9876543210");
  });

  test("rejects an invalid helpline number [ADM-SET-03]", async ({ page }) => {
    await page.getByLabel("Helpline number", { exact: true }).fill("abc");
    await page.getByRole("button", { name: "Save Helpline number" }).click();
    await expect(page.getByText("Helpline number saved.")).toHaveCount(0);
    // Nothing invalid was stored: the saved value is still the seeded one.
    await page.reload();
    await expect(page.getByLabel("Helpline number", { exact: true })).not.toHaveValue("abc");
  });
});

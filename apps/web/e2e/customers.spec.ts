import { expect, test } from "@playwright/test";
import { chooseSite, signInAsAdmin } from "./helpers";

test.describe("Customers (scenario C02)", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
    await page.getByRole("link", { name: "Customers", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Customers" })).toBeVisible();
    await chooseSite(page, /TEST C02/);
  });

  test("lists seeded test customers and finds one by search", async ({ page }) => {
    await expect(page.getByRole("link", { name: /^Test / }).first()).toBeVisible();
    await page.getByLabel(/Search by name/).fill("test.c02@priveo.test");
    await expect(page.locator("tbody tr").filter({ hasText: "test.c02@priveo.test" })).toBeVisible();
    await expect(page.locator("tbody tr").filter({ hasText: "test.c07@priveo.test" })).toHaveCount(0);
  });

  test("shows the summary numbers and the status tabs", async ({ page }) => {
    const tiles = page.getByRole("region", { name: "Customer summary" });
    await expect(tiles.getByRole("button", { name: /^Total customers: [1-9]/ })).toBeVisible();
    await expect(page.getByRole("tab", { name: /^All/ })).toHaveAttribute("aria-selected", "true");
    await page.getByRole("tab", { name: /^No subscription/ }).click();
    await expect(page.getByRole("tab", { name: /^No subscription/ })).toHaveAttribute("aria-selected", "true");
  });

  test("an unknown search shows the empty state", async ({ page }) => {
    await page.getByLabel(/Search by name/).fill("zzz-no-such-customer");
    await expect(page.getByText("No customers found")).toBeVisible();
  });

  test("opens a customer detail page, in tabs", async ({ page }) => {
    await page.getByLabel(/Search by name/).fill("test.c02@priveo.test");
    await page.locator("tbody tr").filter({ hasText: "test.c02@priveo.test" }).getByRole("link").first().click();
    await expect(page).toHaveURL(/\/customers\/[0-9a-f-]{36}$/);
    await expect(page.getByRole("tab", { name: "Account details" })).toHaveAttribute("aria-selected", "true");
    await page.getByRole("tab", { name: /^Vehicles/ }).click();
    await expect(page).toHaveURL(/tab=vehicles/);
    await expect(page.getByRole("button", { name: "Add vehicle" }).first()).toBeVisible();
  });
});

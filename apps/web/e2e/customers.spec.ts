import { expect, test } from "@playwright/test";
import { signInAsAdmin } from "./helpers";

test.describe("Customers (scenario C02)", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
  });

  test("lists seeded test customers and finds one by search", async ({ page }) => {
    await page.getByRole("link", { name: "Customers", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Customers" })).toBeVisible();
    await expect(page.getByRole("link", { name: /^Test / }).first()).toBeVisible();

    await page.getByLabel(/Search by name/).fill("test.c02@priveo.test");
    await expect(page.getByRole("row", { name: /test\.c02@priveo\.test/ })).toBeVisible();
    await expect(page.getByRole("row", { name: /test\.c07@priveo\.test/ })).toHaveCount(0);
  });

  test("an unknown search shows the empty state", async ({ page }) => {
    await page.goto("customers");
    await page.getByLabel(/Search by name/).fill("zzz-no-such-customer");
    await expect(page.getByText("No customers found.")).toBeVisible();
  });

  test("opens a customer detail page", async ({ page }) => {
    await page.goto("customers");
    await page.getByLabel(/Search by name/).fill("test.c02@priveo.test");
    await page.getByRole("row", { name: /test\.c02@priveo\.test/ }).getByRole("link").click();
    await expect(page).toHaveURL(/\/customers\/[0-9a-f-]{36}$/);
  });
});

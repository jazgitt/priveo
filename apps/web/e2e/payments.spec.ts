import { expect, test } from "@playwright/test";
import { scenario, signInAsAdmin } from "./helpers";

// A01 holds an Initiated payment (the customer says they paid). Confirming it
// mutates the fixture database; the stack rebuilds that database every run.
test.describe("Payments (scenario A01)", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
  });

  test("confirms an Initiated payment, then issues a GST invoice", async ({ page }) => {
    const a01 = scenario("A01");
    await page.getByRole("link", { name: "Payments", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Payments" })).toBeVisible();

    await page.getByLabel("Customer ID").fill(a01.customer_id);
    await page.getByLabel("Status", { exact: true }).selectOption("Initiated");
    await page.getByRole("button", { name: "Apply" }).click();

    const row = page.getByRole("row", { name: /Initiated/ }).first();
    await expect(row).toBeVisible();
    await row.getByRole("button", { name: "Open" }).click();

    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("(GST included)")).toBeVisible();
    await dialog.getByRole("button", { name: "Confirm received" }).click();
    await expect(page.getByText("Payment confirmed.")).toBeVisible();
    await expect(dialog.getByText("Received", { exact: true })).toBeVisible();

    await dialog.getByRole("button", { name: /Issue invoice|View invoice/ }).click();
    const invoice = dialog.getByRole("region", { name: "Invoice" });
    await expect(invoice).toBeVisible();
    await expect(invoice.getByText(/including GST/)).toBeVisible();
    await expect(invoice.getByText(/GSTIN/)).toBeVisible();
  });

  test("a filter with no matches shows the empty state", async ({ page }) => {
    await page.goto("payments");
    await page.getByLabel("Customer ID").fill("00000000-0000-0000-0000-000000000000");
    await page.getByRole("button", { name: "Apply" }).click();
    await expect(page.getByText("No payments match these filters.")).toBeVisible();
  });
});

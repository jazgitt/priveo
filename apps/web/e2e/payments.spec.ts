import { expect, test } from "@playwright/test";
import { choose, chooseSite, signInAsAdmin } from "./helpers";

// A01 holds an Initiated payment (the customer says they paid). Confirming it
// mutates the fixture database; the stack rebuilds that database every run.
test.describe("Payments (scenario A01)", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
    await page.getByRole("link", { name: "Payments", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Payments" })).toBeVisible();
    await chooseSite(page, /TEST A01/);
  });

  test("confirms an Initiated payment, then issues a GST invoice", async ({ page }) => {
    await choose(page, "Status", "Initiated");
    const row = page.locator("tbody tr").filter({ hasText: "Initiated" }).first();
    await expect(row).toBeVisible();
    await row.getByRole("button", { name: "Open" }).click();

    const dialog = page.getByRole("dialog");
    await expect(dialog.getByText("(GST included)")).toBeVisible();
    await dialog.getByRole("button", { name: "Confirm received" }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Confirm received" }).click();
    await expect(page.getByText("Payment confirmed.")).toBeVisible();
    await expect(dialog.getByText("Received", { exact: true })).toBeVisible();

    await dialog.getByRole("button", { name: /Issue invoice|View invoice/ }).click();
    const confirmInvoice = page.getByRole("alertdialog");
    if (await confirmInvoice.isVisible()) await confirmInvoice.getByRole("button", { name: "Issue invoice" }).click();
    const invoice = dialog.getByRole("region", { name: "Invoice" });
    await expect(invoice).toBeVisible();
    await expect(invoice.getByText(/including GST/)).toBeVisible();
    await expect(invoice.getByText(/GSTIN/)).toBeVisible();
  });

  test("a summary tile filters the list by status", async ({ page }) => {
    const tiles = page.getByRole("region", { name: "Payment summary" });
    await expect(tiles.getByRole("button", { name: /^All payments: [1-9]/ })).toBeVisible();
    await tiles.getByRole("button", { name: /^Initiated: [1-9]/ }).click();
    await expect(page.locator("tbody tr").first()).toBeVisible();
    await expect(page.locator("tbody tr td:nth-child(7)").filter({ hasNotText: "Initiated" })).toHaveCount(0);
  });

  test("a filter with no matches shows the empty state", async ({ page }) => {
    await page.getByLabel("Due after").fill("2099-01-01");
    await expect(page.getByText("No payments match these filters")).toBeVisible();
  });
});

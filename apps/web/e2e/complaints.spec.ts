import { expect, test } from "@playwright/test";
import { choose, chooseSite, signInAsAdmin } from "./helpers";

// C12 holds Raised / In progress / Resolved complaints, one older than 4 hours.
test.describe("Complaints (scenario C12)", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
    await page.getByRole("link", { name: "Complaints", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Complaints" })).toBeVisible();
    await chooseSite(page, /TEST C12/);
  });

  test("filters by status and marks the overdue complaint", async ({ page }) => {
    const rows = page.locator("tbody tr");
    await expect(rows.first()).toBeVisible();
    await expect(page.locator("tbody").getByText("Overdue", { exact: true }).first()).toBeVisible();

    await choose(page, "Status", "Resolved");
    await expect(rows.filter({ hasText: "Resolved" }).first()).toBeVisible();
    // Status is the 7th column.
    await expect(page.locator("tbody tr td:nth-child(7)").filter({ hasNotText: "Resolved" })).toHaveCount(0);
  });

  test("a summary tile filters the list too", async ({ page }) => {
    const tiles = page.getByRole("region", { name: "Complaint summary" });
    await expect(tiles.getByRole("button", { name: /^Total complaints: \d+/ })).toBeVisible();
    await tiles.getByRole("button", { name: /^Resolved: \d+/ }).click();
    await expect(page.locator("tbody tr td:nth-child(7)").filter({ hasNotText: "Resolved" })).toHaveCount(0);
  });

  test("resolves a raised complaint with a note", async ({ page }) => {
    await choose(page, "Status", "Raised");
    await page.locator("tbody tr").filter({ hasText: "Raised" }).first().getByRole("link").click();
    await expect(page).toHaveURL(/\/complaints\/[0-9a-f-]{36}$/);

    await choose(page, "Set status", "Resolved");
    await page.getByLabel("Note for the customer").fill("E2E: washed again and checked with the customer.");
    await page.getByRole("button", { name: "Change status" }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Change status" }).click();
    await expect(page.getByText("E2E: washed again and checked with the customer.")).toBeVisible();
  });
});

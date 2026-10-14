import { expect, test } from "@playwright/test";
import { signInAsAdmin } from "./helpers";

// C12 holds Raised / In progress / Resolved complaints, one older than 4 hours.
test.describe("Complaints (scenario C12)", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
  });

  test("filters by status and marks the overdue complaint", async ({ page }) => {
    await page.getByRole("link", { name: "Complaints", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Complaints" })).toBeVisible();
    await expect(page.locator(".sp-overdue").first()).toBeVisible();

    await page.getByLabel("Status").selectOption("Resolved");
    await expect(page.locator("tbody tr").filter({ hasText: "Resolved" }).first()).toBeVisible();
    // Status is the 6th column; society names also contain the word "Raised".
    await expect(page.locator("tbody tr td:nth-child(6)").filter({ hasNotText: "Resolved" })).toHaveCount(0);
  });

  test("resolves a raised complaint with a note", async ({ page }) => {
    await page.goto("complaints");
    await page.getByLabel("Status").selectOption("Raised");
    await page.locator("tbody tr").filter({ hasText: "Raised" }).first().getByRole("link").click();
    await expect(page).toHaveURL(/\/complaints\/[0-9a-f-]{36}$/);

    await page.getByLabel("Set status").selectOption("Resolved");
    await page.getByLabel("Note for the customer").fill("E2E: washed again and checked with the customer.");
    await page.getByRole("button", { name: "Change status" }).click();
    await expect(page.getByText("E2E: washed again and checked with the customer.")).toBeVisible();
  });
});

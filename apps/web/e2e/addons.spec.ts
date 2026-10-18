import { expect, test } from "@playwright/test";
import { choose, chooseSite, signInAsAdmin } from "./helpers";

// C21 has Requested, Scheduled, Missed and Cancelled Deep Spa bookings.
test.describe("Add on Service Requests (scenario C21)", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
    await page.getByRole("link", { name: "Add on Service Requests", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Add on Service Requests" })).toBeVisible();
    await chooseSite(page, /TEST C21/);
  });

  const bookings = (page: import("@playwright/test").Page) => page.locator("tbody tr").filter({ hasText: "Deep Spa" });

  test("lists the four seeded bookings", async ({ page }) => {
    const rows = bookings(page);
    await expect(rows).toHaveCount(4);
    for (const status of ["Requested", "Scheduled", "Missed", "Cancelled"]) {
      await expect(rows.filter({ hasText: status }).first()).toBeVisible();
    }
  });

  test("cancels a requested booking", async ({ page }) => {
    const rows = bookings(page);
    await expect(rows).toHaveCount(4);
    await choose(page, "Status filter", "Requested");
    await expect(rows).toHaveCount(1);
    await rows.first().getByRole("button", { name: "Open" }).click();

    const dialog = page.getByRole("dialog");
    await dialog.getByRole("button", { name: "Cancel booking" }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Cancel booking" }).click();
    await expect(page.getByText("Booking cancelled.")).toBeVisible();
    await dialog.getByRole("button", { name: "Close" }).click();

    await expect(rows).toHaveCount(0);
    await choose(page, "Status filter", "Cancelled");
    await expect(rows).toHaveCount(2);
  });
});

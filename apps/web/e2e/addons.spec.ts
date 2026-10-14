import { expect, test } from "@playwright/test";
import { optionValue, signInAsAdmin } from "./helpers";

// C21 has Requested, Scheduled, Missed and Cancelled Deep Spa bookings.
test.describe("Add-ons (scenario C21)", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
    await page.getByRole("link", { name: "Add-ons", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Add-ons" })).toBeVisible();
    const society = page.getByLabel("Society filter");
    await society.selectOption(await optionValue(society, "TEST C21"));
  });

  test("lists the four seeded bookings", async ({ page }) => {
    const cards = page.locator(".card", { hasText: "Deep Spa ·" });
    await expect(cards).toHaveCount(4);
    for (const status of ["Requested", "Scheduled", "Missed", "Cancelled"]) {
      await expect(cards.filter({ hasText: status }).first()).toBeVisible();
    }
  });

  test("cancels a requested booking", async ({ page }) => {
    const cards = page.locator(".card", { hasText: "Deep Spa ·" });
    await expect(cards).toHaveCount(4);
    await page.getByLabel("Status filter").selectOption("Requested");
    await expect(cards).toHaveCount(1);
    await cards.first().getByRole("button", { name: "Cancel booking" }).click();

    await expect(cards).toHaveCount(0);
    await page.getByLabel("Status filter").selectOption("Cancelled");
    await expect(cards).toHaveCount(2);
  });
});

import { expect, test } from "@playwright/test";
import { chooseSite, signInAsAdmin } from "./helpers";

test.describe("Crew (scenarios R04, R06)", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
    await page.getByRole("link", { name: "Crew", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Crew", exact: true })).toBeVisible();
  });

  test("finds a crew member by mobile number and opens the detail page [ADM-CRW-07, ADM-CRW-24]", async ({ page }) => {
    await chooseSite(page, /TEST R06/);
    await page.getByLabel("Search").fill("9800035000");
    const rows = page.locator("tbody tr");
    await expect(rows).toHaveCount(1);
    await rows.first().getByRole("link").first().click();
    await expect(page).toHaveURL(/\/crew\/[0-9a-f-]{36}$/);
  });

  test("R04 shows an inactive crew member and a locked login [ADM-CRW-15, CRW-ACC-07]", async ({ page }) => {
    await chooseSite(page, /TEST R04/);
    await expect(page.locator("tbody tr").first()).toBeVisible();
    const table = page.locator("tbody");
    await expect(table.getByText("Locked", { exact: true }).first()).toBeVisible();
    await expect(table.getByText("Inactive", { exact: true }).first()).toBeVisible();
  });

  test("the role tabs narrow the list [ADM-CRW-07]", async ({ page }) => {
    await chooseSite(page, /TEST R06/);
    await expect(page.locator("tbody tr")).toHaveCount(3);
    await page.getByRole("tab", { name: /^Trainees/ }).click();
    await expect(page.locator("tbody tr")).toHaveCount(1);
  });

  test("a summary tile filters the list and the tile view shows the same crew [ADM-CRW-27]", async ({ page }) => {
    await chooseSite(page, /TEST R04/);
    const tiles = page.getByRole("region", { name: "Crew summary" });
    await expect(page.locator("tbody tr").first()).toBeVisible();
    const inactive = tiles.getByRole("button", { name: /^Inactive: [1-9]/ });
    await inactive.click();
    await expect(page.locator("tbody tr").first()).toBeVisible();
    await expect(page.locator("tbody").getByText("Active", { exact: true })).toHaveCount(0);

    await page.getByRole("button", { name: "Tiles" }).click();
    await expect(page.getByRole("table")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "List" })).toHaveAttribute("aria-pressed", "false");
  });
});

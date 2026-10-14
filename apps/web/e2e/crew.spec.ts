import { expect, test } from "@playwright/test";
import { optionValue, signInAsAdmin } from "./helpers";

test.describe("Crew (scenarios R04, R06)", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
    await page.getByRole("link", { name: "Crew", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Crew", exact: true })).toBeVisible();
  });

  test("finds a crew member by mobile number and opens the detail page", async ({ page }) => {
    await page.getByLabel("Search").fill("9800035000");
    const rows = page.locator("tbody tr");
    await expect(rows).toHaveCount(1);
    await rows.first().getByRole("link").click();
    await expect(page).toHaveURL(/\/crew\/[0-9a-f-]{36}$/);
  });

  test("R04 shows an inactive crew member and a locked login", async ({ page }) => {
    const society = page.getByLabel("Society", { exact: true });
    await society.selectOption(await optionValue(society, "TEST R04"));
    await expect(page.locator("tbody tr").first()).toBeVisible();
    const table = page.locator("tbody");
    await expect(table.getByText("Locked", { exact: true }).first()).toBeVisible();
    await expect(table.getByText("Inactive", { exact: true }).first()).toBeVisible();
  });

  test("the role filter narrows the list", async ({ page }) => {
    const society = page.getByLabel("Society", { exact: true });
    await society.selectOption(await optionValue(society, "TEST R06"));
    await expect(page.locator("tbody tr")).toHaveCount(3);
    await page.getByLabel("Role").selectOption("Trainee");
    await expect(page.locator("tbody tr")).toHaveCount(1);
  });
});

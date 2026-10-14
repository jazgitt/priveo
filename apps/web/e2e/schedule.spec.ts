import { expect, test } from "@playwright/test";
import { addDays, optionValue, scenario, signInAsAdmin } from "./helpers";

// R06 has a Draft schedule (as_of + 1 day) and a Frozen one (as_of + 3 days).
test.describe("Schedule (scenario R06)", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
    await page.getByRole("link", { name: "Schedule", exact: true }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Schedule" })).toBeVisible();
  });

  async function openBoard(page: import("@playwright/test").Page, date: string) {
    const society = page.getByLabel("Society", { exact: true });
    await society.selectOption(await optionValue(society, "TEST R06"));
    await page.getByLabel("Start date").fill(date);
  }

  test("freezes a draft schedule", async ({ page }) => {
    await openBoard(page, addDays(scenario("R06").as_of, 1));
    const board = page.getByRole("region", { name: /Board/ }).or(page.locator(".card", { hasText: "Board" }));
    await expect(board.getByText("Draft", { exact: true })).toBeVisible();

    await board.getByRole("button", { name: "Freeze" }).click();
    const dialog = page.getByRole("dialog", { name: "Freeze this schedule?" });
    await dialog.getByRole("button", { name: "Freeze" }).click();

    await expect(board.getByText("Frozen", { exact: true })).toBeVisible();
    await expect(board.getByRole("button", { name: "Unfreeze" })).toBeVisible();
  });

  test("a frozen schedule refuses a wrong unfreeze code", async ({ page }) => {
    await openBoard(page, addDays(scenario("R06").as_of, 3));
    const board = page.locator(".card", { hasText: "Board" });
    await expect(board.getByText("Frozen", { exact: true })).toBeVisible();

    await board.getByRole("button", { name: "Unfreeze" }).click();
    const dialog = page.getByRole("dialog", { name: "Unfreeze with the code" });
    await dialog.getByLabel("Code").fill("definitely-wrong");
    await dialog.getByRole("button", { name: "Unfreeze" }).click();

    await expect(dialog.getByRole("alert")).toBeVisible();
    await dialog.getByRole("button", { name: "Cancel" }).click();
    await expect(board.getByText("Frozen", { exact: true })).toBeVisible();
  });
});

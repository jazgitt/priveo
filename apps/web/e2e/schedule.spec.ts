import { expect, test } from "@playwright/test";
import { addDays, scenario, signInAsAdmin } from "./helpers";

// R06 has a Draft schedule (as_of + 1 day) and a Frozen one (as_of + 3 days).
test.describe("Schedule (scenario R06)", () => {
  test.beforeEach(async ({ page }) => {
    await signInAsAdmin(page);
    await page.getByRole("link", { name: "Schedule", exact: true }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Schedule" })).toBeVisible();
  });

  async function openBoard(page: import("@playwright/test").Page, date: string) {
    // The site is chosen in the sidebar; the day leads the page and its schedule sits under the day strip.
    await page.getByRole("combobox", { name: "Site" }).click();
    await page.getByRole("option", { name: /TEST R06/ }).click();
    await page.getByLabel("Day", { exact: true }).fill(date);
  }

  test("freezes a draft schedule [ADM-SCH-16]", async ({ page }) => {
    await openBoard(page, addDays(scenario("R06").as_of, 1));
    const board = page.getByRole("group", { name: "Schedule of this day" });
    await expect(board.getByText("Draft", { exact: true })).toBeVisible();

    await board.getByRole("button", { name: "Freeze" }).click();
    const dialog = page.getByRole("alertdialog", { name: "Freeze this schedule?" });
    await dialog.getByRole("button", { name: "Freeze" }).click();

    await expect(board.getByText("Frozen", { exact: true })).toBeVisible();
    await expect(board.getByRole("button", { name: "Unfreeze" })).toBeVisible();
  });

  test("a frozen schedule refuses a wrong unfreeze code [ADM-SCH-18]", async ({ page }) => {
    await openBoard(page, addDays(scenario("R06").as_of, 3));
    const board = page.getByRole("group", { name: "Schedule of this day" });
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

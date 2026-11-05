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

  // Real mouse drags (native drag and drop), against the real API. These run before the test that
  // freezes the draft day, and each puts its card back, so the later tests see the day as they expect.
  const lane = (page: import("@playwright/test").Page, name: string) => page.getByRole("region", { name, exact: true });
  const carOf = (page: import("@playwright/test").Page, name: string) => lane(page, name).getByRole("button", { name: /TS35TT0001/ });

  test("dragging a card to another crew member's free slot moves it, and it is still there after a reload [ADM-SCH-33]", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await openBoard(page, addDays(scenario("R06").as_of, 1));
    await expect(carOf(page, "TEST R06 Member 1")).toContainText("06:00-06:20");

    // Drop it at the top of the Manager's free slot: it starts at the slot's start, to the nearest 5 minutes.
    await carOf(page, "TEST R06 Member 1").dragTo(lane(page, "TEST R06 Manager 0").getByLabel("Free 05:00-14:00"),
      { targetPosition: { x: 30, y: 2 } });
    await expect(carOf(page, "TEST R06 Manager 0")).toContainText(/05:0[05]-05:[2][05]/);
    await expect(carOf(page, "TEST R06 Member 1")).toHaveCount(0);
    await expect(page.getByText(/moved to TEST R06 Manager 0 at 05:0[05]/)).toBeVisible();

    await page.reload();
    await expect(page.getByRole("group", { name: "Day board" })).toBeVisible();
    await expect(carOf(page, "TEST R06 Manager 0")).toContainText(/05:0[05]-05:[2][05]/);

    // And back, by dragging it onto the first lane's free time.
    await carOf(page, "TEST R06 Manager 0").dragTo(lane(page, "TEST R06 Member 1").getByLabel("Free 05:00-14:00"),
      { targetPosition: { x: 30, y: 2 } });
    await expect(carOf(page, "TEST R06 Member 1")).toBeVisible();
    await expect(carOf(page, "TEST R06 Manager 0")).toHaveCount(0);
  });

  test("dragging a card onto Unscheduled asks first, and takes it off its crew member [ADM-SCH-33]", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await openBoard(page, addDays(scenario("R06").as_of, 1));
    const unscheduled = page.getByTestId("col-unscheduled");
    await carOf(page, "TEST R06 Member 1").dragTo(unscheduled.locator(".sch-col-body"));
    const ask = page.getByRole("alertdialog");
    await expect(ask).toContainText("off");
    // Cancelling leaves the card where it was.
    await ask.getByRole("button", { name: "Cancel" }).click();
    await expect(carOf(page, "TEST R06 Member 1")).toBeVisible();

    await carOf(page, "TEST R06 Member 1").dragTo(unscheduled.locator(".sch-col-body"));
    await page.getByRole("alertdialog").getByRole("button", { name: "Take off crew member" }).click();
    await expect(unscheduled.getByRole("button", { name: /TS35TT0001/ })).toBeVisible();
    await page.reload();
    await expect(page.getByTestId("col-unscheduled").getByRole("button", { name: /TS35TT0001/ })).toBeVisible();

    // Back onto a crew member: it takes that member's first free time.
    await page.getByTestId("col-unscheduled").getByRole("button", { name: /TS35TT0001/ })
      .dragTo(lane(page, "TEST R06 Member 1").locator(".sch-col-body"));
    await expect(carOf(page, "TEST R06 Member 1")).toBeVisible();
    await expect(page.getByTestId("col-unscheduled").getByRole("button", { name: /TS35TT0001/ })).toHaveCount(0);
  });

  test("a drop on a frozen schedule is refused: the card goes back and the day offers the code [ADM-SCH-33]", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await openBoard(page, addDays(scenario("R06").as_of, 3));
    await expect(carOf(page, "TEST R06 Member 1")).toBeVisible();
    await carOf(page, "TEST R06 Member 1").dragTo(lane(page, "TEST R06 Manager 0").getByLabel("Free 05:00-14:00"),
      { targetPosition: { x: 30, y: 2 } });
    const alert = page.getByRole("alert").filter({ hasText: /frozen/i });
    await expect(alert).toBeVisible();
    await expect(alert.getByRole("button", { name: "Unfreeze with code" })).toBeVisible();
    // The optimistic move was undone, and the server kept it where it was.
    await expect(carOf(page, "TEST R06 Member 1")).toBeVisible();
    await expect(carOf(page, "TEST R06 Manager 0")).toHaveCount(0);
    await page.reload();
    await expect(carOf(page, "TEST R06 Member 1")).toBeVisible();
  });

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

  test("the board fills the window and the day strip folds away [ADM-SCH-33]", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await openBoard(page, addDays(scenario("R06").as_of, 1));
    const board = page.getByRole("group", { name: "Day board" });
    await expect(board).toBeVisible();
    const fits = async () => {
      const box = (await board.boundingBox())!;
      const doc = await page.evaluate(() => document.documentElement.scrollHeight - window.innerHeight);
      return { height: box.height, bottom: box.y + box.height, overflow: doc };
    };
    const open = await fits();
    expect(open.bottom).toBeLessThanOrEqual(768);
    expect(open.overflow).toBeLessThanOrEqual(0);
    expect(open.height).toBeGreaterThan(300);

    await page.getByRole("button", { name: "Hide days" }).click();
    const folded = await fits();
    expect(folded.height).toBeGreaterThan(open.height);
    expect(folded.overflow).toBeLessThanOrEqual(0);
    await page.reload();
    await expect(page.getByRole("button", { name: "Show days" })).toBeVisible();
  });

  test("the Table view lists the jobs with their crew member and finds one by search [ADM-SCH-33]", async ({ page }) => {
    await openBoard(page, addDays(scenario("R06").as_of, 1));
    await page.getByRole("button", { name: /Table/ }).click();
    const table = page.getByRole("region", { name: "Jobs of the day" });
    await expect(table.getByRole("columnheader", { name: "Crew" })).toBeVisible();
    const rows = table.getByRole("row");
    await expect(rows).toHaveCount(2); // the heading row and the one job of this fixture
    await expect(rows.nth(1)).toContainText("TEST R06 Member 1");
    await page.getByRole("searchbox", { name: "Find a job" }).fill("no-such-car");
    await expect(table.getByText("No job matches the search and filters.")).toBeVisible();
    await page.getByRole("searchbox", { name: "Find a job" }).fill("member 1");
    await expect(rows).toHaveCount(2);
  });

  test("the Focus view fills the window and the job dialog opens over it [ADM-SCH-33]", async ({ page }) => {
    await page.setViewportSize({ width: 1366, height: 768 });
    await openBoard(page, addDays(scenario("R06").as_of, 1));
    await page.getByRole("button", { name: /Focus/ }).click();
    const focus = page.getByRole("dialog", { name: "Schedule board, focus view" });
    await expect(focus).toBeVisible();
    // The dialog zooms in as it opens; wait until it has settled to the full window.
    await expect.poll(async () => (await focus.boundingBox())!.width).toBeGreaterThanOrEqual(1360);
    await expect.poll(async () => (await focus.boundingBox())!.height).toBeGreaterThanOrEqual(760);
    await expect(focus.getByRole("tablist")).toHaveCount(0);
    const lanes = focus.getByRole("group", { name: "Day board" });
    expect((await lanes.boundingBox())!.height).toBeGreaterThan(450);

    await focus.getByRole("button", { name: /TS35TT0001/ }).click();
    const job = page.getByRole("dialog", { name: /TS35TT0001/ });
    await expect(job).toBeVisible();
    // The job dialog is on top: its Cancel button can be clicked.
    await job.getByRole("button", { name: "Cancel" }).click();
    await expect(job).toHaveCount(0);
    await page.keyboard.press("Escape");
    await expect(focus).toHaveCount(0);
  });

  test("the board opens alone in a new browser tab, signed in, on the same day [ADM-SCH-33]", async ({ page, context }) => {
    const day = addDays(scenario("R06").as_of, 1);
    await openBoard(page, day);
    const [tab] = await Promise.all([
      context.waitForEvent("page"),
      page.getByRole("link", { name: /New tab/ }).click(),
    ]);
    await tab.waitForLoadState();
    await expect(tab).toHaveURL(new RegExp(`/schedule/board\\?date=${day}`));
    await expect(tab.getByRole("group", { name: "Day board" })).toBeVisible();
    await expect(tab.getByLabel("Day", { exact: true })).toHaveValue(day);
    // No sidebar, no tabs: only the board.
    await expect(tab.getByRole("navigation", { name: "Admin areas" })).toHaveCount(0);
    await expect(tab.getByRole("tablist")).toHaveCount(0);
  });

  test("Unscheduled stays pinned while the lanes scroll, and the board pans by dragging [ADM-SCH-33]", async ({ page }) => {
    // Wide enough for the sidebar, narrow enough that the four columns do not fit.
    await page.setViewportSize({ width: 1100, height: 700 });
    await openBoard(page, addDays(scenario("R06").as_of, 1));
    const board = page.getByRole("group", { name: "Day board" });
    const pinned = page.getByTestId("col-unscheduled");
    await expect(pinned).toBeVisible();
    const scrollable = await board.evaluate((el) => el.scrollWidth - el.clientWidth);
    expect(scrollable).toBeGreaterThan(50);

    const left = async () => (await pinned.boundingBox())!.x - (await board.boundingBox())!.x;
    const before = await left();
    await board.evaluate((el) => { el.scrollLeft = 120; });
    expect(Math.abs((await left()) - before)).toBeLessThan(2);

    // A real drag of the heading of a lane pans the board.
    await board.evaluate((el) => { el.scrollLeft = 0; });
    const head = page.getByTestId("col-c0").or(page.locator(".sch-col-head").nth(1));
    const box = (await head.first().boundingBox())!;
    await page.mouse.move(box.x + box.width - 20, box.y + 6);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width - 120, box.y + 6, { steps: 6 });
    await page.mouse.up();
    expect(await board.evaluate((el) => el.scrollLeft)).toBeGreaterThan(40);
  });

  test("a lane folds to a thin strip and unfolds again [ADM-SCH-33]", async ({ page }) => {
    await openBoard(page, addDays(scenario("R06").as_of, 1));
    const lane = page.getByRole("region", { name: "TEST R06 Manager 0" });
    const wide = (await lane.boundingBox())!.width;
    await page.getByRole("button", { name: "Fold TEST R06 Manager 0's lane" }).click();
    const strip = page.getByRole("region", { name: "TEST R06 Manager 0, folded" });
    await expect(strip).toBeVisible();
    expect((await strip.boundingBox())!.width).toBeLessThan(wide / 3);
    await page.reload();
    await expect(page.getByRole("region", { name: "TEST R06 Manager 0, folded" })).toBeVisible();
    await page.getByRole("button", { name: "Show TEST R06 Manager 0's lane" }).click();
    await expect(page.getByRole("region", { name: "TEST R06 Manager 0" })).toBeVisible();
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

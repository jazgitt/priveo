import { expect, test } from "@playwright/test";
import { ADMIN_LOGIN, signIn, signInAsAdmin } from "./helpers";

test.describe("Admin sign-in", () => {
  test("wrong password is rejected and stays on the sign-in form [ADM-ACC-06]", async ({ page }) => {
    await signIn(page, ADMIN_LOGIN, "not-the-password");
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Priveo" })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Admin areas" })).toHaveCount(0);
  });

  test("a protected page redirects an anonymous visitor to sign-in [ADM-ACC-02]", async ({ page }) => {
    await page.goto("payments");
    await expect(page.getByLabel("User ID")).toBeVisible();
  });

  test("admin signs in, sees every area and signs out [ADM-ACC-01, ADM-ACC-06]", async ({ page }) => {
    await signInAsAdmin(page);
    const nav = page.getByRole("navigation", { name: "Admin areas" });
    for (const area of ["Dashboard", "Customers", "Payments", "Complaints", "Schedule", "Settings", "Audit"]) {
      await expect(nav.getByRole("link", { name: area, exact: true })).toBeVisible();
    }
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page.getByLabel("User ID")).toBeVisible();
    // The session is really gone, not just hidden.
    await page.goto("customers");
    await expect(page.getByLabel("User ID")).toBeVisible();
  });

  test("the session survives a reload [ADM-ACC-12]", async ({ page }) => {
    await signInAsAdmin(page);
    await page.reload();
    await expect(page.getByRole("navigation", { name: "Admin areas" })).toBeVisible();
  });
});

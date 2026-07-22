import { expect, test } from "./fixtures/seed.fixture";

test.describe("Navigation @smoke", () => {
  test("header links route to main pages", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Run exam" })).toBeVisible();

    const nav = page.locator(".app-nav");
    await nav.getByRole("link", { name: /^Results/ }).click();
    await expect(page).toHaveURL(/\/verify/);
    await expect(page.getByRole("heading", { name: "Results" })).toBeVisible();

    await nav.getByRole("link", { name: "Reports", exact: true }).click();
    await expect(page).toHaveURL(/\/export/);
    await expect(page.getByRole("heading", { name: "Reports" })).toBeVisible();

    await nav.getByRole("link", { name: "Advanced", exact: true }).click();
    await expect(page).toHaveURL(/\/advanced\/calibrator/);

    await nav.getByRole("link", { name: "Run exam", exact: true }).click();
    await expect(page).toHaveURL("/");
  });
});

test("shows pending badge on Results when items exist", async ({ page, seededVerification }) => {
  await page.goto("/");
  await expect(page.locator(".nav-count")).toBeVisible();
  expect(seededVerification.itemId).toBeGreaterThan(0);
});

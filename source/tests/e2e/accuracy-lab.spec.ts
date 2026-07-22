import { expect, test } from "./fixtures/seed.fixture";

test.describe("Accuracy Lab @smoke", () => {
  test("loads page and lists fixtures", async ({ page }) => {
    await page.goto("/advanced/accuracy");
    await expect(page.getByRole("heading", { name: "Accuracy Lab" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Layout Calibrator" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Run validation" })).toBeVisible();
  });

  test("sub-nav routes between advanced tools", async ({ page }) => {
    await page.goto("/advanced/accuracy");
    await page.getByRole("link", { name: "Layout Calibrator" }).click();
    await expect(page).toHaveURL(/\/advanced\/calibrator/);
    await expect(page.getByRole("heading", { name: "Layout Calibrator" })).toBeVisible();

    await page.getByRole("link", { name: "Accuracy Lab" }).click();
    await expect(page).toHaveURL(/\/advanced\/accuracy/);
  });
});

test("run validation shows alignment summary", async ({ page }) => {
  test.slow();
  await page.goto("/advanced/accuracy");
  await page.locator("#acc-source").selectOption("sample_scan_2");
  await page.getByRole("button", { name: "Run validation" }).click();
  await expect(page.getByText(/Quality \d+\.\d+/)).toBeVisible({ timeout: 120_000 });
});

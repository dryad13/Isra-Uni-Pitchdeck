import { expect, test } from "./fixtures/seed.fixture";
import { ReportsPage } from "./pages/reports.page";

test.describe("Reports export @critical", () => {
  test("shows score table and triggers CSV export", async ({ page, seededExport }) => {
    const reports = new ReportsPage(page);
    await reports.goto();

    await reports.selectProgramById(seededExport.programId);
    await reports.selectSessionById(seededExport.sessionId);

    const scoreTable = page.locator(".data-table");
    await expect(scoreTable).toBeVisible({ timeout: 15_000 });
    await expect(scoreTable.getByRole("cell", { name: seededExport.rollNo })).toBeVisible();

    const downloadPromise = page.waitForEvent("download");
    const popupPromise = page.waitForEvent("popup");
    await reports.exportButton.click();
    const [download] = await Promise.all([downloadPromise, popupPromise]);
    expect(download.suggestedFilename()).toMatch(/session_\d+_literal\.csv$/);
  });
});

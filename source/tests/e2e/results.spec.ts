import { expect, test } from "./fixtures/seed.fixture";
import { ResultsPage } from "./pages/results.page";

test.describe("Results verification @critical", () => {
  test("keyboard resolve decreases pending count", async ({ page, seededVerification }) => {
    const results = new ResultsPage(page);
    await results.goto();
    await results.setupBatchReview(
      seededVerification.programId,
      seededVerification.sessionId,
      seededVerification.batchId,
    );

    const before = await results.pendingCount();
    expect(before).toBeGreaterThan(0);

    await results.selectFirstBatchReviewRow();
    await results.resolveWithKeyboard("A");

    await expect.poll(async () => results.pendingCount()).toBeLessThan(before);
    expect(seededVerification.itemId).toBeGreaterThan(0);
  });
});

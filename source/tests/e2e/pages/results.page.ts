import { Locator, Page, expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class ResultsPage extends BasePage {
  readonly pendingLozenge: Locator;
  readonly batchReviewRows: Locator;

  constructor(page: Page) {
    super(page);
    this.pendingLozenge = page.locator(".lozenge");
    this.batchReviewRows = page.locator(".batch-review-row");
  }

  async goto(): Promise<void> {
    await this.gotoPath("/verify");
    await expect(this.page.getByRole("heading", { name: "Results" })).toBeVisible();
  }

  async setupBatchReview(programId: number, sessionId: number, batchId: number): Promise<void> {
    await this.page.locator("#review-program").selectOption(String(programId));
    await this.page.locator("#review-session").selectOption(String(sessionId));
    await this.page.locator("#review-batch").selectOption(String(batchId));
    await expect(this.batchReviewRows.first()).toBeVisible({ timeout: 15_000 });
  }

  async pendingCount(): Promise<number> {
    const text = await this.pendingLozenge.first().textContent();
    const match = text?.match(/(\d+)\s+pending/);
    return match ? Number(match[1]) : 0;
  }

  async selectFirstBatchReviewRow(): Promise<void> {
    await this.batchReviewRows.first().click();
  }

  async resolveWithKeyboard(option: string): Promise<void> {
    await this.page.keyboard.press(option);
    await this.page.keyboard.press("Enter");
  }
}

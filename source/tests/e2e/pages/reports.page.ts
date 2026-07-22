import { Locator, Page, expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class ReportsPage extends BasePage {
  readonly programSelect: Locator;
  readonly scopeSelect: Locator;
  readonly exportButton: Locator;

  constructor(page: Page) {
    super(page);
    this.programSelect = page.locator("#exp-program");
    this.scopeSelect = page.locator("#exp-scope");
    this.exportButton = page.getByRole("button", { name: /Export/ });
  }

  async goto(): Promise<void> {
    await this.gotoPath("/export");
    await expect(this.page.getByRole("heading", { name: "Reports" })).toBeVisible();
  }

  async selectProgramById(id: number): Promise<void> {
    const sessionsPromise = this.page.waitForResponse(
      (resp) => resp.url().includes(`/programs/${id}/sessions`) && resp.status() === 200,
    );
    await this.programSelect.selectOption(String(id));
    await sessionsPromise;
    await expect(this.scopeSelect).toBeEnabled();
  }

  async selectSessionById(id: number): Promise<void> {
    await expect(this.scopeSelect.locator(`option[value="${id}"]`)).toBeAttached();
    const scoresPromise = this.page.waitForResponse(
      (resp) => resp.url().includes(`/sessions/${id}/scores`) && resp.status() === 200,
    );
    await this.scopeSelect.selectOption(String(id));
    await scoresPromise;
  }
}

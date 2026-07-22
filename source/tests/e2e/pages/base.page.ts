import { Locator, Page, expect } from "@playwright/test";

export abstract class BasePage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async gotoPath(path: string): Promise<void> {
    await this.page.goto(path);
    await this.page.waitForLoadState("networkidle");
  }

  protected nav = () => this.page.locator(".app-nav");

  async openFromNav(linkName: string): Promise<void> {
    await this.gotoPath("/");
    await this.nav().getByRole("link", { name: new RegExp(`^${linkName}`) }).click();
    await this.page.waitForLoadState("networkidle");
  }
}

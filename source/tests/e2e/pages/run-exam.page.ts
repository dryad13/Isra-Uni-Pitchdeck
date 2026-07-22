import { Locator, Page, expect } from "@playwright/test";
import { BasePage } from "./base.page";

export class RunExamPage extends BasePage {
  readonly stepper: Locator;
  readonly programSelect: Locator;
  readonly newProgramInput: Locator;
  readonly createProgramButton: Locator;
  readonly sessionNameInput: Locator;
  readonly addSessionButton: Locator;

  constructor(page: Page) {
    super(page);
    this.stepper = page.getByRole("navigation", { name: "Exam setup progress" });
    this.programSelect = page.locator("#program-select");
    this.newProgramInput = page.locator("#new-program");
    this.createProgramButton = page.getByRole("button", { name: "Create exam" });
    this.sessionNameInput = page.locator("#session-name");
    this.addSessionButton = page.getByRole("button", { name: "Add session" });
  }

  async goto(): Promise<void> {
    await this.gotoPath("/");
    await expect(this.page.getByRole("heading", { name: "Run exam" })).toBeVisible();
  }

  async createProgram(name: string): Promise<void> {
    await this.newProgramInput.fill(name);
    await this.createProgramButton.click();
    await expect(this.programSelect).toHaveValue(/\d+/);
  }

  async createSession(name: string): Promise<void> {
    await this.sessionNameInput.fill(name);
    await this.addSessionButton.click();
    await expect(this.page.getByRole("radio", { name: new RegExp(name) })).toBeVisible();
  }

  async uploadAnswerKeyFile(filePath: string): Promise<void> {
    await this.page.getByRole("tab", { name: "Upload file" }).click();
    await this.page.locator("#key-file").setInputFiles(filePath);
  }

  async selectSession(name: string): Promise<void> {
    await this.page.getByRole("radio", { name: new RegExp(name) }).click();
  }

  async expectKeyReady(): Promise<void> {
    await expect(this.page.getByText(/\d+\/\d+ answers · ready/).first()).toBeVisible({
      timeout: 15_000,
    });
  }

  async expectStep3Available(): Promise<void> {
    await expect(this.page.getByRole("button", { name: "Start scan" })).toBeEnabled();
  }
}

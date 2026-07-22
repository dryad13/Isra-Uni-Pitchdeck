import { expect, test } from "./fixtures/seed.fixture";

test.describe("Roster page", () => {
  test("loads roster nav and program selector", async ({ page, seededProgramSession }) => {
    await page.goto("/roster");
    await expect(page.getByRole("heading", { name: "Student roster" })).toBeVisible();
    await expect(page.getByLabel("Exam program")).toBeVisible();
    expect(seededProgramSession.programId).toBeGreaterThan(0);
  });
});

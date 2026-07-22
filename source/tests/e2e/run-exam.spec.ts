import path from "path";
import { expect, test } from "./fixtures/seed.fixture";
import { RunExamPage } from "./pages/run-exam.page";

const KEY_CSV = path.join(process.cwd(), "tests/fixtures/test_key.csv");

test.describe("Run exam wizard", () => {
  test("@smoke creates program and session via UI", async ({ page }) => {
    const runExam = new RunExamPage(page);
    await runExam.goto();
    const name = `UI Exam ${Date.now()}`;
    await runExam.createProgram(name);
    await runExam.createSession("Paper 1");
    await runExam.selectSession("Paper 1");
    await expect(runExam.page.getByRole("heading", { name: "Load the answer key" })).toBeVisible();
  });

  test("@critical uploads answer key CSV and unlocks step 3", async ({ page, seededProgramSession }) => {
    const runExam = new RunExamPage(page);
    await runExam.goto();
    await runExam.programSelect.selectOption({ label: seededProgramSession.programName });
    await runExam.selectSession(seededProgramSession.sessionName);
    await runExam.uploadAnswerKeyFile(KEY_CSV);
    await runExam.expectKeyReady();
    await runExam.expectStep3Available();
  });

  test("@critical blocks step 3 when key incomplete", async ({ page, seededProgramSession }) => {
    const runExam = new RunExamPage(page);
    await runExam.goto();
    await runExam.programSelect.selectOption({ label: seededProgramSession.programName });
    await runExam.selectSession(seededProgramSession.sessionName);
    await expect(runExam.page.getByText(/Finish the answer key/i)).toBeVisible();
    await expect(runExam.page.getByRole("button", { name: "Start scan" })).toHaveCount(0);
  });
});

import path from "path";
import { expect, test, FIXTURES_DIR } from "./fixtures/api.fixture";

test.describe("Answer keys API @critical", () => {
  test("CSV upload marks key ready", async ({ programsApi, sessionsApi, answerKeysApi }) => {
    const program = await (await programsApi.create(`Key Prog ${Date.now()}`)).json();
    const session = await (
      await sessionsApi.create(program.id, {
        name: "Key Session",
        template_family: "150Q",
        sheet_question_count: 3,
      })
    ).json();

    const csvPath = path.join(FIXTURES_DIR, "test_key.csv");
    const upload = await answerKeysApi.uploadCsv(program.id, session.id, csvPath);
    expect(upload.status()).toBe(200);

    const status = await sessionsApi.keyStatus(session.id);
    expect(status.status()).toBe(200);
    const body = await status.json();
    expect(body.ready).toBe(true);
    expect(body.filled).toBe(3);

    await programsApi.remove(program.id);
  });
});

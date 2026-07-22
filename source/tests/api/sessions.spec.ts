import { expect, test } from "./fixtures/api.fixture";

test.describe("Sessions API @smoke", () => {
  test("create session and suggest-start", async ({ programsApi, sessionsApi }) => {
    const program = await (await programsApi.create(`Sess Prog ${Date.now()}`)).json();
    const session = await (
      await sessionsApi.create(program.id, {
        name: "Paper 1",
        template_family: "150Q",
        sheet_question_count: 3,
      })
    ).json();

    expect(session.global_q_start).toBe(1);
    expect(session.global_q_end).toBe(3);

    const suggest = await sessionsApi.suggestStart(program.id);
    expect(suggest.status()).toBe(200);
    expect((await suggest.json()).global_q_start).toBe(4);

    await programsApi.remove(program.id);
  });
});

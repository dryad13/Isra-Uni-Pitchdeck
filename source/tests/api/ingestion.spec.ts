import { expect, test } from "./fixtures/api.fixture";

test.describe("Ingestion API @smoke", () => {
  test("start/stop toggles watching", async ({ programsApi, sessionsApi, ingestionApi }) => {
    const program = await (await programsApi.create(`Ing Prog ${Date.now()}`)).json();
    const session = await (
      await sessionsApi.create(program.id, {
        name: "Ing Session",
        template_family: "150Q",
        sheet_question_count: 3,
      })
    ).json();

    const start = await ingestionApi.start(session.id);
    expect(start.status()).toBe(200);

    const status = await ingestionApi.status();
    expect(status.status()).toBe(200);
    const body = await status.json();
    expect(body.watching).toBe(true);
    expect(body.active_session_id).toBe(session.id);
    expect(body).toHaveProperty("dropzone_path");

    const stop = await ingestionApi.stop();
    expect(stop.status()).toBe(200);
    const afterStop = await ingestionApi.status();
    expect((await afterStop.json()).watching).toBe(false);

    await programsApi.remove(program.id);
  });
});

import { expect, test } from "./fixtures/api.fixture";
import { createProgramSessionWithKeys, seedScoredSheet } from "./helpers/seed";

test.describe("Export API @critical", () => {
  test("CSV export returns header row", async ({ request, exportApi, programsApi }) => {
    const { programId, sessionId } = await createProgramSessionWithKeys(request);
    await seedScoredSheet(request, sessionId);

    const scores = await exportApi.scores(sessionId);
    expect(scores.status()).toBe(200);
    const scoreBody = await scores.json();
    expect(scoreBody.sheet_count).toBe(1);

    const exportRes = await exportApi.downloadExport(sessionId, "literal", "csv");
    expect(exportRes.status()).toBe(200);
    expect(exportRes.headers()["content-type"]).toContain("text/csv");
    const text = await exportRes.text();
    expect(text.length).toBeGreaterThan(0);

    await programsApi.remove(programId);
  });
});

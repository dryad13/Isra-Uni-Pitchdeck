import { expect, test } from "./fixtures/api.fixture";
import { createProgramSessionWithKeys, seedVerification } from "./helpers/seed";

test.describe("Verification API @critical", () => {
  test("resolve confirm removes pending item", async ({ request, verificationApi, programsApi }) => {
    const { programId, sessionId } = await createProgramSessionWithKeys(request);
    const itemId = await seedVerification(request, sessionId);

    const pending = await verificationApi.pending();
    const items = (await pending.json()).items;
    expect(items.some((i: { id: number }) => i.id === itemId)).toBe(true);

    const resolve = await verificationApi.resolve(itemId, "confirm", "A");
    expect(resolve.status()).toBe(200);

    const after = (await verificationApi.pending()).json();
    const remaining = (await after).items;
    expect(remaining.every((i: { id: number }) => i.id !== itemId)).toBe(true);

    await programsApi.remove(programId);
  });
});

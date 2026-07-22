import { expect, test } from "./fixtures/api.fixture";

test.describe("Programs API @smoke", () => {
  const created: number[] = [];

  test.afterEach(async ({ programsApi }) => {
    for (const id of created.splice(0).reverse()) {
      await programsApi.remove(id);
    }
  });

  test("CRUD lifecycle", async ({ programsApi }) => {
    const create = await programsApi.create(`Prog ${Date.now()}`);
    expect(create.status()).toBe(201);
    const program = await create.json();
    created.push(program.id);

    const list = await programsApi.list();
    expect(list.status()).toBe(200);
    const names = (await list.json()).programs.map((p: { name: string }) => p.name);
    expect(names).toContain(program.name);

    const del = await programsApi.remove(program.id);
    expect(del.status()).toBe(204);
    created.pop();
  });

  test("returns 404 for missing program", async ({ programsApi }) => {
    const res = await programsApi.getById(999999);
    expect(res.status()).toBe(404);
  });
});

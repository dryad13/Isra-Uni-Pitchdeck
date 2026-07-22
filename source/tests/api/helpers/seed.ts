import { APIRequestContext } from "@playwright/test";
import fs from "fs";
import path from "path";
import { FIXTURES_DIR } from "../fixtures/api.fixture";

export async function createProgramSessionWithKeys(request: APIRequestContext) {
  const suffix = Date.now();
  const programRes = await request.post("/api/programs", { data: { name: `API Exam ${suffix}` } });
  const program = await programRes.json();

  const sessionRes = await request.post(`/api/programs/${program.id}/sessions`, {
    data: { name: `Session ${suffix}`, template_family: "150Q", sheet_question_count: 3 },
  });
  const session = await sessionRes.json();

  const csvPath = path.join(FIXTURES_DIR, "test_key.csv");
  await request.post(`/api/programs/${program.id}/answer-keys/upload`, {
    multipart: {
      file: {
        name: "test_key.csv",
        mimeType: "text/csv",
        buffer: fs.readFileSync(csvPath),
      },
      session_id: String(session.id),
    },
  });

  return { programId: program.id as number, sessionId: session.id as number };
}

export async function seedVerification(
  request: APIRequestContext,
  sessionId: number,
): Promise<number> {
  const res = await request.post("/api/test/seed-verification", {
    data: { session_id: sessionId },
  });
  if (!res.ok()) throw new Error(`seed-verification failed: ${await res.text()}`);
  const body = await res.json();
  return body.item_id as number;
}

export async function seedScoredSheet(request: APIRequestContext, sessionId: number) {
  const res = await request.post("/api/test/seed-scored-sheet", {
    data: { session_id: sessionId },
  });
  if (!res.ok()) throw new Error(`seed-scored-sheet failed: ${await res.text()}`);
  return res.json();
}

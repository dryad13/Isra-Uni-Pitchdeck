import fs from "fs";
import path from "path";
import { APIRequestContext } from "@playwright/test";

const FIXTURES = path.join(process.cwd(), "tests/fixtures");

export async function seedProgramSession(request: APIRequestContext) {
  const suffix = Date.now();
  const program = await (
    await request.post("/api/programs", { data: { name: `E2E Exam ${suffix}` } })
  ).json();
  const session = await (
    await request.post(`/api/programs/${program.id}/sessions`, {
      data: {
        name: `E2E Session ${suffix}`,
        template_family: "150Q",
        sheet_question_count: 3,
      },
    })
  ).json();
  return {
    programId: program.id as number,
    sessionId: session.id as number,
    programName: program.name as string,
    sessionName: session.name as string,
  };
}

export async function seedProgramSessionWithKeys(request: APIRequestContext) {
  const seeded = await seedProgramSession(request);
  const csv = fs.readFileSync(path.join(FIXTURES, "test_key.csv"));
  await request.post(`/api/programs/${seeded.programId}/answer-keys/upload`, {
    multipart: {
      file: { name: "test_key.csv", mimeType: "text/csv", buffer: csv },
      session_id: String(seeded.sessionId),
    },
  });
  return seeded;
}

export async function seedVerificationItem(request: APIRequestContext, sessionId: number) {
  const res = await request.post("/api/test/seed-verification", {
    data: { session_id: sessionId },
  });
  if (!res.ok()) throw new Error(await res.text());
  const body = await res.json();
  return {
    itemId: body.item_id as number,
    batchId: body.batch_id as number,
  };
}

export async function seedScoredSheetForExport(
  request: APIRequestContext,
  sessionId: number,
  rollNo = `E2E${Date.now()}`,
) {
  const res = await request.post("/api/test/seed-scored-sheet", {
    data: { session_id: sessionId, roll_no: rollNo },
  });
  if (!res.ok()) throw new Error(await res.text());
  return rollNo;
}

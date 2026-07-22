import fs from "fs";
import path from "path";
import { APIRequestContext } from "@playwright/test";
import { BaseApiClient } from "./base-api-client";

export class AnswerKeysApiClient extends BaseApiClient {
  constructor(request: APIRequestContext) {
    super(request, "");
  }

  upsert(
    programId: number,
    sessionId: number,
    entries: { question_no: number; correct_option: string }[],
  ) {
    return this.request.post(`/api/programs/${programId}/answer-keys`, {
      data: { session_id: sessionId, entries },
    });
  }

  uploadCsv(programId: number, sessionId: number, filePath: string) {
    const buffer = fs.readFileSync(filePath);
    return this.request.post(`/api/programs/${programId}/answer-keys/upload`, {
      multipart: {
        file: {
          name: path.basename(filePath),
          mimeType: "text/csv",
          buffer,
        },
        session_id: String(sessionId),
      },
    });
  }
}

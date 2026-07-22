import { APIRequestContext } from "@playwright/test";
import { BaseApiClient } from "./base-api-client";

export class IngestionApiClient extends BaseApiClient {
  constructor(request: APIRequestContext) {
    super(request, "/api/ingestion");
  }

  status() {
    return this.get("/status");
  }

  start(sessionId: number) {
    return this.post("/start", { session_id: sessionId });
  }

  stop() {
    return this.post("/stop");
  }
}

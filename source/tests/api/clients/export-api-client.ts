import { APIRequestContext } from "@playwright/test";
import { BaseApiClient } from "./base-api-client";

export class ExportApiClient extends BaseApiClient {
  constructor(request: APIRequestContext) {
    super(request, "");
  }

  scores(sessionId: number) {
    return this.request.get(`/api/sessions/${sessionId}/scores`);
  }

  downloadExport(sessionId: number, mode: string, format: string) {
    return this.request.get(`/api/sessions/${sessionId}/export`, {
      params: { mode, format },
    });
  }
}

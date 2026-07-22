import { APIRequestContext } from "@playwright/test";
import { BaseApiClient } from "./base-api-client";

export type SessionCreate = {
  name: string;
  template_family: string;
  sheet_question_count: number;
};

export class SessionsApiClient extends BaseApiClient {
  constructor(request: APIRequestContext) {
    super(request, "");
  }

  create(programId: number, payload: SessionCreate) {
    return this.request.post(`/api/programs/${programId}/sessions`, { data: payload });
  }

  suggestStart(programId: number) {
    return this.request.get(`/api/programs/${programId}/sessions/suggest-start`);
  }

  keyStatus(sessionId: number) {
    return this.request.get(`/api/sessions/${sessionId}/key-status`);
  }

  remove(sessionId: number) {
    return this.request.delete(`/api/sessions/${sessionId}`);
  }
}

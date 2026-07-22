import { APIRequestContext } from "@playwright/test";
import { BaseApiClient } from "./base-api-client";

export class VerificationApiClient extends BaseApiClient {
  constructor(request: APIRequestContext) {
    super(request, "/api/verification");
  }

  pending() {
    return this.get("/pending");
  }

  resolve(itemId: number, action: string, resolvedValue?: string) {
    return this.request.post(`/api/verification/${itemId}/resolve`, {
      data: { action, resolved_value: resolvedValue },
    });
  }
}

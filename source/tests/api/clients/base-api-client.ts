import { APIRequestContext, APIResponse } from "@playwright/test";

export class BaseApiClient {
  protected readonly request: APIRequestContext;
  protected readonly basePath: string;

  constructor(request: APIRequestContext, basePath = "") {
    this.request = request;
    this.basePath = basePath;
  }

  protected get(path: string, params?: Record<string, string>): Promise<APIResponse> {
    const url = params
      ? `${this.basePath}${path}?${new URLSearchParams(params)}`
      : `${this.basePath}${path}`;
    return this.request.get(url);
  }

  protected post(path: string, data?: unknown): Promise<APIResponse> {
    return this.request.post(`${this.basePath}${path}`, { data });
  }

  protected delete(path: string): Promise<APIResponse> {
    return this.request.delete(`${this.basePath}${path}`);
  }
}

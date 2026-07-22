import { APIRequestContext } from "@playwright/test";
import { BaseApiClient } from "./base-api-client";

export type Program = {
  id: number;
  name: string;
};

export class ProgramsApiClient extends BaseApiClient {
  constructor(request: APIRequestContext) {
    super(request, "/api/programs");
  }

  list() {
    return this.get("");
  }

  create(name: string) {
    return this.post("", { name });
  }

  getById(id: number) {
    return this.get(`/${id}`);
  }

  remove(id: number) {
    return this.delete(`/${id}`);
  }
}

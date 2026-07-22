import { test as base } from "@playwright/test";
import { AnswerKeysApiClient } from "../clients/answer-keys-api-client";
import { ExportApiClient } from "../clients/export-api-client";
import { IngestionApiClient } from "../clients/ingestion-api-client";
import { ProgramsApiClient } from "../clients/programs-api-client";
import { SessionsApiClient } from "../clients/sessions-api-client";
import { VerificationApiClient } from "../clients/verification-api-client";

export type ApiFixtures = {
  programsApi: ProgramsApiClient;
  sessionsApi: SessionsApiClient;
  answerKeysApi: AnswerKeysApiClient;
  ingestionApi: IngestionApiClient;
  verificationApi: VerificationApiClient;
  exportApi: ExportApiClient;
};

export const test = base.extend<ApiFixtures>({
  programsApi: async ({ request }, use) => {
    await use(new ProgramsApiClient(request));
  },
  sessionsApi: async ({ request }, use) => {
    await use(new SessionsApiClient(request));
  },
  answerKeysApi: async ({ request }, use) => {
    await use(new AnswerKeysApiClient(request));
  },
  ingestionApi: async ({ request }, use) => {
    await use(new IngestionApiClient(request));
  },
  verificationApi: async ({ request }, use) => {
    await use(new VerificationApiClient(request));
  },
  exportApi: async ({ request }, use) => {
    await use(new ExportApiClient(request));
  },
});

export { expect } from "@playwright/test";

export const FIXTURES_DIR = `${process.cwd()}/tests/fixtures`;

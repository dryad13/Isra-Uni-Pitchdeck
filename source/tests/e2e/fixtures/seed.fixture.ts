import { test as base } from "@playwright/test";
import {
  seedProgramSession,
  seedProgramSessionWithKeys,
  seedScoredSheetForExport,
  seedVerificationItem,
} from "../helpers/seed";

export type SeedFixtures = {
  seededProgramSession: { programId: number; sessionId: number; programName: string; sessionName: string };
  seededExam: { programId: number; sessionId: number; programName: string; sessionName: string };
  seededVerification: { programId: number; sessionId: number; itemId: number; batchId: number };
  seededExport: { programId: number; sessionId: number; programName: string; sessionName: string; rollNo: string };
};

export const test = base.extend<SeedFixtures>({
  seededProgramSession: async ({ request }, use) => {
    const seeded = await seedProgramSession(request);
    await use(seeded);
    await request.delete(`/api/programs/${seeded.programId}`);
  },

  seededExam: async ({ request }, use) => {
    const seeded = await seedProgramSessionWithKeys(request);
    await use(seeded);
    await request.delete(`/api/programs/${seeded.programId}`);
  },

  seededVerification: async ({ request }, use) => {
    const seeded = await seedProgramSessionWithKeys(request);
    const verification = await seedVerificationItem(request, seeded.sessionId);
    await use({
      programId: seeded.programId,
      sessionId: seeded.sessionId,
      itemId: verification.itemId,
      batchId: verification.batchId,
    });
    await request.delete(`/api/programs/${seeded.programId}`);
  },

  seededExport: async ({ request }, use) => {
    const seeded = await seedProgramSessionWithKeys(request);
    const rollNo = await seedScoredSheetForExport(request, seeded.sessionId);
    await use({ ...seeded, rollNo });
    await request.delete(`/api/programs/${seeded.programId}`);
  },
});

export { expect } from "@playwright/test";

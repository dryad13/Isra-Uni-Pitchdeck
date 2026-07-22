import { describe, expect, it } from "vitest";
import { deriveStepStates } from "./stepStates";

describe("deriveStepStates", () => {
  it.each([
    [false, false, false, ["active", "locked", "locked"]],
    [true, false, false, ["done", "active", "locked"]],
    [true, true, true, ["done", "done", "active"]],
    [true, true, false, ["done", "done", "active"]],
  ] as const)("(%s, %s, %s) -> %j", (hasSession, keyReady, scanning, expected) => {
    expect(deriveStepStates(hasSession, keyReady, scanning)).toEqual(expected);
  });
});

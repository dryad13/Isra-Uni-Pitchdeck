export type StepState = "done" | "active" | "locked";

export function deriveStepStates(
  hasSession: boolean,
  keyReady: boolean,
  scanning: boolean,
): [StepState, StepState, StepState] {
  if (!hasSession) return ["active", "locked", "locked"];
  if (!keyReady) return ["done", "active", "locked"];
  if (scanning) return ["done", "done", "active"];
  return ["done", "done", "active"];
}

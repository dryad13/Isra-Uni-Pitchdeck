type StepState = "done" | "active" | "locked";

type Props = {
  step1: StepState;
  step2: StepState;
  step3: StepState;
};

const LABELS = ["Choose exam", "Load answer key", "Process sheets"];

export default function Stepper({ step1, step2, step3 }: Props) {
  const steps = [step1, step2, step3];

  return (
    <nav className="stepper" aria-label="Exam setup progress">
      {steps.map((state, i) => (
        <div
          key={i}
          className={`stepper-step stepper-step-${state}`}
          aria-current={state === "active" ? "step" : undefined}
        >
          <span className="stepper-num">{state === "done" ? "✓" : i + 1}</span>
          <span>{LABELS[i]}</span>
        </div>
      ))}
    </nav>
  );
}

export { deriveStepStates } from "./stepStates";
export type { StepState } from "./stepStates";

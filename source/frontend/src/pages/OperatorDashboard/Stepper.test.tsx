import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Stepper from "./Stepper";

describe("Stepper", () => {
  it("renders three step labels", () => {
    render(<Stepper step1="active" step2="locked" step3="locked" />);
    expect(screen.getByText("Choose exam")).toBeInTheDocument();
    expect(screen.getByText("Load answer key")).toBeInTheDocument();
    expect(screen.getByText("Process sheets")).toBeInTheDocument();
  });

  it("marks active step with aria-current", () => {
    render(<Stepper step1="done" step2="active" step3="locked" />);
    const nav = screen.getByRole("navigation", { name: "Exam setup progress" });
    expect(nav.querySelector('[aria-current="step"]')).toHaveTextContent("Load answer key");
  });

  it("shows checkmark on done steps", () => {
    render(<Stepper step1="done" step2="done" step3="active" />);
    const checks = screen.getAllByText("✓");
    expect(checks.length).toBe(2);
  });
});

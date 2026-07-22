import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Lozenge from "../components/Lozenge";

describe("Lozenge", () => {
  it("renders visible text label", () => {
    render(<Lozenge appearance="success">Ready</Lozenge>);
    expect(screen.getByText("Ready")).toBeInTheDocument();
  });

  it("applies appearance class", () => {
    render(<Lozenge appearance="warning">3 pending</Lozenge>);
    const el = screen.getByText("3 pending");
    expect(el.className).toContain("lozenge-warning");
  });
});

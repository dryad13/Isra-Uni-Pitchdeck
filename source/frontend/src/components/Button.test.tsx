import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Button from "./Button";

describe("Button", () => {
  it("renders link variant", () => {
    render(<Button variant="link">Edit</Button>);
    expect(screen.getByRole("button", { name: "Edit" })).toHaveClass("btn-link");
  });

  it("renders danger-link variant", () => {
    render(<Button variant="danger-link">delete</Button>);
    expect(screen.getByRole("button", { name: "delete" })).toHaveClass("btn-danger-link");
  });

  it("calls onClick", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Go</Button>);
    await user.click(screen.getByRole("button", { name: "Go" }));
    expect(onClick).toHaveBeenCalledOnce();
  });
});

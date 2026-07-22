import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Tabs from "./Tabs";

describe("Tabs", () => {
  it("switches tabs on click", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <Tabs
        items={[
          { id: "a", label: "Tab A" },
          { id: "b", label: "Tab B" },
        ]}
        activeId="a"
        onChange={onChange}
      />,
    );
    await user.click(screen.getByRole("tab", { name: "Tab B" }));
    expect(onChange).toHaveBeenCalledWith("b");
  });

  it("marks active tab", () => {
    render(
      <Tabs
        items={[
          { id: "a", label: "Tab A" },
          { id: "b", label: "Tab B" },
        ]}
        activeId="b"
        onChange={() => {}}
      />,
    );
    expect(screen.getByRole("tab", { name: "Tab B" })).toHaveAttribute("aria-selected", "true");
  });
});

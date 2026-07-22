import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import PageLayout from "./PageLayout";

describe("PageLayout", () => {
  it("renders title and children", () => {
    render(
      <PageLayout title="Reports" subtitle="Export scores">
        <p>Content</p>
      </PageLayout>,
    );
    expect(screen.getByRole("heading", { name: "Reports" })).toBeInTheDocument();
    expect(screen.getByText("Export scores")).toBeInTheDocument();
    expect(screen.getByText("Content")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(
      <PageLayout
        title="Empty"
        empty={{ title: "Nothing here", description: "Try again" }}
      />,
    );
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });
});

describe("ExamScopePicker", () => {
  it("renders program select", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ programs: [{ id: 1, name: "Midterm" }] }),
      }),
    );
    const { default: ExamScopePicker } = await import("./ExamScopePicker");
    render(
      <MemoryRouter>
        <ExamScopePicker
          levels="program"
          value={{ programId: null, sessionId: null, batchId: null }}
          onChange={() => {}}
        />
      </MemoryRouter>,
    );
    expect(screen.getByLabelText("Exam program")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});

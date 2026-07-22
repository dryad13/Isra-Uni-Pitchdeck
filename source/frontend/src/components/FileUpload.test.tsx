import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import FileUpload from "../components/FileUpload";

describe("FileUpload", () => {
  it("calls onFile when a file is chosen", async () => {
    const onFile = vi.fn();
    render(<FileUpload id="test-file" onFile={onFile} />);
    const input = document.getElementById("test-file") as HTMLInputElement;
    const file = new File(["a"], "sample.csv", { type: "text/csv" });
    await userEvent.upload(input, file);
    expect(onFile).toHaveBeenCalled();
    expect(screen.getByText("sample.csv")).toBeInTheDocument();
  });

  it("clears selected file name", async () => {
    const onFile = vi.fn();
    render(<FileUpload id="clear-file" onFile={onFile} />);
    const input = document.getElementById("clear-file") as HTMLInputElement;
    await userEvent.upload(input, new File(["a"], "one.csv", { type: "text/csv" }));
    await userEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(screen.queryByText("one.csv")).not.toBeInTheDocument();
  });
});

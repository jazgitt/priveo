import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button, Dialog, StatusChip, Table, TextField, ToastProvider, useToast } from ".";

describe("components", () => {
  it("Button is disabled while busy", () => {
    render(<Button busy>Save</Button>);
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("TextField links its label and error", () => {
    render(<TextField label="Mobile" error="Use 10 digits." />);
    const input = screen.getByLabelText("Mobile");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Use 10 digits.");
  });

  it("Table renders rows and an empty message", () => {
    const columns = [{ key: "n", header: "Name", render: (r: { n: string }) => r.n }];
    const { rerender } = render(<Table columns={columns} rows={[{ n: "Asha" }]} rowKey={(r) => r.n} />);
    expect(screen.getByRole("columnheader", { name: "Name" })).toBeInTheDocument();
    expect(screen.getByText("Asha")).toBeInTheDocument();
    rerender(<Table columns={columns} rows={[]} rowKey={(r) => r.n} empty="No crew." />);
    expect(screen.getByText("No crew.")).toBeInTheDocument();
  });

  it("StatusChip shows its label", () => {
    render(<StatusChip tone="warn">Over due</StatusChip>);
    expect(screen.getByText("Over due")).toHaveClass("chip-warn");
  });

  it("Dialog closes on Escape", async () => {
    const onClose = vi.fn();
    render(<Dialog open title="Confirm" onClose={onClose}>Sure?</Dialog>);
    expect(screen.getByRole("dialog", { name: "Confirm" })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
  });

  it("Toast shows a message", async () => {
    function Trigger() {
      const toast = useToast();
      return <button onClick={() => toast.show("Saved", "ok")}>go</button>;
    }
    render(<ToastProvider><Trigger /></ToastProvider>);
    await userEvent.click(screen.getByText("go"));
    expect(screen.getByText("Saved")).toBeInTheDocument();
  });
});

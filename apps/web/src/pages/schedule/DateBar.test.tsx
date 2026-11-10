import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DateBar } from "./DateBar";

function renderBar(onChange = vi.fn(), extra: Partial<Parameters<typeof DateBar>[0]> = {}) {
  render(
    <DateBar title="Schedule" site="Palm Grove" date="2026-11-14" today="2026-11-08" from="2026-11-01" to="2026-11-22"
             scheduleOf={new Map()} attention={new Set()} onChange={onChange} startFolded={false} {...extra}>
      <span>status here</span>
    </DateBar>,
  );
  return onChange;
}

describe("the day bar (ADM-SCH-35)", () => {
  it("has a Today button right after the date selectors that sets the day to today", async () => {
    const onChange = renderBar();
    const today = screen.getByRole("button", { name: "Today" });
    // It follows the next-day arrow in the same row.
    expect(screen.getByRole("button", { name: "Next day" }).nextElementSibling).toBe(today);
    await userEvent.click(today);
    expect(onChange).toHaveBeenCalledWith("2026-11-08");
  });

  it("keeps the header on one row; the chosen day's schedule sits under the strip", () => {
    renderBar();
    const row = screen.getByRole("heading", { name: "Schedule" }).parentElement!;
    expect(row).toHaveClass("flex-nowrap");
    expect(row).not.toHaveClass("flex-wrap");
    expect(row).toContainElement(screen.getByRole("button", { name: "Hide days" }));
    expect(row).not.toContainElement(screen.getByText("status here"));
    expect(screen.getByText("status here")).toBeInTheDocument();
  });

  it("names the days of the strip in the days control, at a smaller size", async () => {
    renderBar(vi.fn(), { startFolded: true });
    const toggle = screen.getByRole("button", { name: "Show days" });
    expect(toggle).toHaveClass("text-[10.5px]");
    // The trail is shown, but the control keeps its name.
    expect(toggle).toHaveTextContent("1 Nov to 22 Nov");
    expect(screen.queryByRole("group", { name: "Days" })).not.toBeInTheDocument();
    await userEvent.click(toggle);
    expect(await screen.findByRole("group", { name: "Days" })).toBeInTheDocument();
  });
});

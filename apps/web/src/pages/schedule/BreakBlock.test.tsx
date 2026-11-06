import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { aroundBreak, BreakBlock, breakOf } from "./BreakBlock";

describe("BreakBlock", () => {
  it("is drawn at the cleaner's break time and is not a drop slot", () => {
    render(<BreakBlock start={570} end={600} />);
    const block = screen.getByLabelText("Break 09:30-10:00");
    expect(block).toHaveTextContent("Break 09:30-10:00");
    expect(block).not.toHaveAttribute("data-slot");
  });

  it("breakOf reads the minutes of the availability row; a cleaner without a break shows none", () => {
    expect(breakOf({ break_start: 570, break_end: 600 })).toEqual({ start: 570, end: 600 });
    expect(breakOf({})).toBeNull();
    expect(breakOf({ break_start: null, break_end: null })).toBeNull();
    expect(breakOf(undefined)).toBeNull();
  });

  it("aroundBreak takes the break out of the windows", () => {
    const day = [{ start: 330, end: 660 }];
    expect(aroundBreak(day, { start: 570, end: 600 })).toEqual([{ start: 330, end: 570 }, { start: 600, end: 660 }]);
    expect(aroundBreak(day, null)).toEqual(day);
    expect(aroundBreak([{ start: 330, end: 540 }], { start: 570, end: 600 })).toEqual([{ start: 330, end: 540 }]);
  });
});

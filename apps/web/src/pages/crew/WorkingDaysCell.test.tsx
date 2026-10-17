import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { defaultHours, type Crew } from "./api";
import { summariseWeek, weekDates, WorkingDaysCell } from "./WorkingDaysCell";

// Wednesday 21-Oct-26: the week is Monday 19-Oct-26 to Sunday 25-Oct-26.
const TODAY = new Date(2026, 9, 21);

function crew(over: Partial<Crew> = {}): Crew {
  const hours = defaultHours().map((h) => (h.day === "Saturday" || h.day === "Sunday"
    ? { ...h, working: false, start: "", end: "" } : { ...h, start: "05:00", end: "14:00" }));
  hours[0] = { ...hours[0], extra_slots: [{ start: "19:00", end: "20:30" }] };
  return {
    id: "c1", name: "Crew1", mobile: "9000000001", society_id: "s1", society: "Lake View",
    role: "Member", active: true, locked: false, working_hours: hours,
    paired_member_id: null, paired_member: "", exceptions: [], ...over,
  };
}

describe("weekDates", () => {
  it("runs Monday to Sunday around the date, also across a month end", () => {
    expect(weekDates(TODAY)).toEqual([
      "2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23", "2026-10-24", "2026-10-25"]);
    expect(weekDates(new Date(2026, 10, 1))[0]).toBe("2026-10-26"); // Sunday 1-Nov-26
  });
});

describe("summariseWeek", () => {
  it("leaves out days off, drops full-day exceptions and marks a late start as partial", () => {
    const week = summariseWeek(crew({ exceptions: [
      { id: "e1", date: "2026-10-20", kind: "Sick", start: "" },
      { id: "e2", date: "2026-10-22", kind: "Late start", start: "09:00" },
    ] }), TODAY);
    const by = Object.fromEntries(week.map((d) => [d.day, d]));
    expect(by.Monday).toMatchObject({ status: "working", hours: "05:00-14:00, 19:00-20:30" });
    expect(by.Tuesday).toMatchObject({ status: "off", note: "Sick on 20-Oct-26" });
    expect(by.Thursday).toMatchObject({ status: "partial", hours: "09:00-14:00" });
    expect(by.Saturday.status).toBe("off");
  });

  it("ignores exceptions that fall in other weeks", () => {
    const week = summariseWeek(crew({ exceptions: [
      { id: "e1", date: "2026-10-27", kind: "Leave", start: "" }] }), TODAY);
    expect(week.filter((d) => d.status === "off").map((d) => d.day)).toEqual(["Saturday", "Sunday"]);
  });
});

describe("WorkingDaysCell", () => {
  it("shows the letters, colours a partial day and gives the detail on hover", () => {
    const { container } = render(<WorkingDaysCell today={TODAY} crew={crew({ exceptions: [
      { id: "e1", date: "2026-10-20", kind: "Sick", start: "" },
      { id: "e2", date: "2026-10-22", kind: "Late start", start: "09:00" },
    ] })} />);
    expect(container.querySelector(".cap-tip-value")).toHaveTextContent("M, W, T, F");
    expect(container.querySelector(".dow-warn")).toHaveTextContent("T");
    const tip = screen.getByRole("tooltip");
    expect(tip).toHaveTextContent("This week, 19-Oct-26 to 25-Oct-26");
    expect(within(tip).getByText("Monday")).toBeInTheDocument();
    expect(tip).toHaveTextContent("05:00-14:00, 19:00-20:30");
    expect(tip).toHaveTextContent("Late start from 09:00 on 22-Oct-26");
    expect(tip).toHaveTextContent("Sick on 20-Oct-26");
    expect(tip).not.toHaveTextContent("Saturday");
  });

  it("says None when no day is worked", () => {
    const off = crew().working_hours.map((h) => ({ ...h, working: false, start: "", end: "" }));
    const { container } = render(<WorkingDaysCell today={TODAY} crew={crew({ working_hours: off })} />);
    expect(container.querySelector(".cap-tip-value")).toHaveTextContent("None");
  });
});

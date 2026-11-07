import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NameRain } from "./NameRain";

const names = ["Asha", "Ravi", "KA01AB1234", "MH12CD5678"];

function reducedMotion(matches: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: matches && query === "(prefers-reduced-motion: reduce)",
    media: query, onchange: null,
    addListener: () => {}, removeListener: () => {},
    addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
  }));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the name rain while the scheduler runs", () => {
  it("drops every name from the props into the falling set, and hides it from assistive tech", () => {
    reducedMotion(false);
    render(<NameRain names={names} active />);
    const rain = screen.getByTestId("name-rain");
    expect(rain).toHaveAttribute("aria-hidden", "true");
    for (const name of names) {
      expect(within(rain).getAllByText(name).length).toBeGreaterThanOrEqual(1);
    }
    // Only names from the props fall.
    for (const item of rain.querySelectorAll(".sch-rain-item")) {
      expect(names).toContain(item.textContent);
    }
  });

  it("shows nothing when no run is active", () => {
    reducedMotion(false);
    render(<NameRain names={names} active={false} />);
    expect(screen.queryByTestId("name-rain")).not.toBeInTheDocument();
  });

  it("shows nothing when there are no names yet", () => {
    reducedMotion(false);
    render(<NameRain names={[]} active />);
    expect(screen.queryByTestId("name-rain")).not.toBeInTheDocument();
  });

  it("shows nothing for an admin who asks for reduced motion", () => {
    reducedMotion(true);
    render(<NameRain names={names} active />);
    expect(screen.queryByTestId("name-rain")).not.toBeInTheDocument();
  });
});

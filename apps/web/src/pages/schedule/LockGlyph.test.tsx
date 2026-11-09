import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LOCK_FILL, LockGlyph, LOCKED_SHACKLE, UNLOCKED_SHACKLE } from "./LockGlyph";

describe("lock icons (P3-1)", () => {
  it("a locked lock has its empty body filled red, and both legs of the shackle in the body", () => {
    const { container } = render(<LockGlyph locked />);
    const svg = container.querySelector("svg")!;
    expect(svg).toHaveAttribute("data-state", "locked");
    expect(svg.querySelector('[data-part="body"]')).toHaveAttribute("fill", "#dc2626");
    expect(svg.querySelector('[data-part="shackle"]')).toHaveAttribute("d", LOCKED_SHACKLE);
  });

  it("an unlocked lock has its empty body filled green, and its shackle swung clear of the body", () => {
    const { container } = render(<LockGlyph locked={false} />);
    const svg = container.querySelector("svg")!;
    expect(svg).toHaveAttribute("data-state", "unlocked");
    expect(svg.querySelector('[data-part="body"]')).toHaveAttribute("fill", "#16a34a");
    expect(svg.querySelector('[data-part="shackle"]')).toHaveAttribute("d", UNLOCKED_SHACKLE);
  });

  it("the two states differ in shape as well as in colour", () => {
    expect(LOCKED_SHACKLE).not.toBe(UNLOCKED_SHACKLE);
    expect(LOCK_FILL.locked).not.toBe(LOCK_FILL.unlocked);
  });

  it("is hidden from assistive technology, which reads the button label instead", () => {
    const { container } = render(<LockGlyph locked />);
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });
});

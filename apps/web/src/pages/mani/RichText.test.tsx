import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RichText } from "./RichText";

describe("RichText", () => {
  it("shows bold text and bullets as such, not as asterisks", () => {
    render(<RichText text={"Here is what I see:\n\n* **Deep Spa**: book one.\n* **Add-ons**: browse them.\n\nAnything else?"} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("Deep Spa").tagName).toBe("STRONG");
    expect(screen.queryByText(/\*\*/)).toBeNull();
    expect(screen.getByText("Anything else?")).toBeTruthy();
  });

  it("makes a numbered list and joins wrapped lines into one paragraph", () => {
    render(<RichText text={"First line\nsecond line\n\n1. one\n2. two"} />);
    expect(screen.getByText("First line second line")).toBeTruthy();
    expect(screen.getByRole("list").tagName).toBe("OL");
  });

  it("never turns the model's text into HTML", () => {
    const { container } = render(<RichText text={"<img src=x onerror=alert(1)> and **bold**"} />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.textContent).toContain("<img src=x onerror=alert(1)>");
  });
});

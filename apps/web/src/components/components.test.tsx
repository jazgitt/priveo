import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { HoverTip, Tabs, TipRows, ToastProvider, useToast } from ".";

describe("components", () => {
  it("Tabs show one panel and move with the arrow keys", async () => {
    function Host() {
      const [tab, setTab] = useState("a");
      return (
        <Tabs tabs={[{ id: "a", label: "First" }, { id: "b", label: "Second" }]} active={tab} label="Parts" onChange={setTab}>
          <p>Panel {tab}</p>
        </Tabs>
      );
    }
    render(<Host />);
    expect(screen.getByText("Panel a")).toBeInTheDocument();
    screen.getByRole("tab", { name: "First" }).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Second" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Panel b")).toBeInTheDocument();
    await userEvent.keyboard("{End}{Home}");
    expect(screen.getByRole("tab", { name: "First" })).toHaveAttribute("aria-selected", "true");
  });

  it("HoverTip lists its rows", () => {
    render(
      <HoverTip label="8 h" ariaLabel="Crew 8 h">
        <TipRows title="Crew" empty="None" rows={[{ key: "a", left: "Asha", right: "8 h", note: "05:00-13:00", tone: "warn" }]} />
      </HoverTip>,
    );
    expect(screen.getByRole("tooltip")).toHaveTextContent("Asha");
    expect(screen.getByRole("tooltip")).toHaveTextContent("05:00-13:00");
  });

  it("Toast shows a message", async () => {
    function Trigger() {
      const toast = useToast();
      return (
        <>
          <button type="button" onClick={() => toast.show("Saved", "ok")}>ok</button>
          <button type="button" onClick={() => toast.show("Failed", "error")}>bad</button>
          <button type="button" onClick={() => toast.show("Note")}>info</button>
        </>
      );
    }
    render(<ToastProvider><Trigger /></ToastProvider>);
    await userEvent.click(screen.getByText("ok"));
    await userEvent.click(screen.getByText("bad"));
    await userEvent.click(screen.getByText("info"));
    expect(await screen.findByText("Saved")).toBeInTheDocument();
    expect(await screen.findByText("Failed")).toBeInTheDocument();
    expect(await screen.findByText("Note")).toBeInTheDocument();
  });
});

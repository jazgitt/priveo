import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { ToastProvider } from "../components";
import { PortalProviders } from "../test/portal";
import { useConfirm } from "./confirm";
import { DataTable, Pager, tableMinRem } from "./DataTable";
import { useViewMode, ViewToggle } from "./view";
import { DetailList, EmptyState, ErrorState, PageHeader, StatTile } from "./layout";
import { errorMessage, useAppMutation } from "./mutation";
import { StatusBadge, toneOf } from "./status";
import { TaskTray, useTasks } from "./tasks";

function mount(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}><MemoryRouter initialEntries={["/"]}><ToastProvider><PortalProviders>
      <Routes>
        <Route path="/" element={<>{ui}<TaskTray /></>} />
        <Route path="/done" element={<p>Result page</p>} />
      </Routes>
    </PortalProviders></ToastProvider></MemoryRouter></QueryClientProvider>,
  );
}

it("turns API errors, plain errors and anything else into a message", () => {
  expect(errorMessage(new ApiError(422, "validation_failed", "Check the form.", { email: "Not an email." }))).toBe("Check the form. Not an email.");
  expect(errorMessage(new Error("Upload failed."))).toBe("Upload failed.");
  expect(errorMessage("odd")).toBe("Something went wrong. Please try again.");
});

it("gives each status one tone", () => {
  expect(toneOf("Active")).toBe("ok");
  expect(toneOf("Over due")).toBe("error");
  expect(toneOf("Something new")).toBe("neutral");
  render(<StatusBadge status="Frozen" />);
  expect(screen.getByText("Frozen")).toHaveClass("text-info");
});

it("shows a running task with its time, then the result with a link", async () => {
  let finish: (v: number) => void = () => {};
  function Starter() {
    const tasks = useTasks();
    return <button type="button" onClick={() => void tasks.start({
      label: "Big job", detail: "Working…",
      run: () => new Promise<number>((r) => { finish = r; }),
      done: (n) => ({ message: `${n} done.`, link: { label: "Open result", to: "/done" } }),
    })}>Start</button>;
  }
  mount(<Starter />);
  await userEvent.click(screen.getByRole("button", { name: "Start" }));
  const running = await screen.findByRole("status");
  expect(running).toHaveTextContent("Big job");
  expect(running).toHaveTextContent("Working… 0:00");
  finish(4);
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("4 done."));
  await userEvent.click(within(screen.getByRole("status")).getByRole("button", { name: "Open result" }));
  expect(await screen.findByText("Result page")).toBeInTheDocument();
});

it("reports a failed task and lets it be dismissed", async () => {
  function Starter() {
    const tasks = useTasks();
    return <button type="button" onClick={() => void tasks.start({
      label: "Big job", detail: "Working…",
      run: () => Promise.reject(new ApiError(500, "boom", "The server failed.")),
      done: () => ({ message: "never" }),
    }).catch(() => {})}>Start</button>;
  }
  mount(<Starter />);
  await userEvent.click(screen.getByRole("button", { name: "Start" }));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("The server failed."));
  await userEvent.click(screen.getByRole("button", { name: "Dismiss" }));
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
});

it("asks before acting and answers false on Cancel", async () => {
  const answers: boolean[] = [];
  function Asker() {
    const confirm = useConfirm();
    return <button type="button" onClick={async () => answers.push(await confirm({
      title: "Delete it?", description: "It goes away.", confirmLabel: "Delete", tone: "danger",
    }))}>Ask</button>;
  }
  mount(<Asker />);
  await userEvent.click(screen.getByRole("button", { name: "Ask" }));
  await userEvent.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Cancel" }));
  await userEvent.click(screen.getByRole("button", { name: "Ask" }));
  await userEvent.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Delete" }));
  await waitFor(() => expect(answers).toEqual([false, true]));
});

it("says Saving, then Saved or the reason it failed", async () => {
  const work = vi.fn().mockResolvedValueOnce("ok").mockRejectedValueOnce(new ApiError(409, "taken", "That name is taken."));
  function Saver() {
    const m = useAppMutation<void>({ mutationFn: work, success: "Saved it." });
    return <button type="button" onClick={() => m.mutate()}>Save</button>;
  }
  mount(<Saver />);
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  expect(await screen.findByText("Saved it.")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  expect(await screen.findByText("That name is taken.")).toBeInTheDocument();
});

it("shows skeleton rows, then rows, cuts long text and opens a row on click or Enter", async () => {
  const opened: string[] = [];
  function List() {
    const [rows, setRows] = useState<{ id: string; name: string }[] | undefined>(undefined);
    return (
      <>
        <button type="button" onClick={() => setRows([{ id: "a", name: "A very long name" }])}>Load</button>
        <DataTable rows={rows} loading={!rows} rowKey={(r) => r.id} empty={<EmptyState title="Nothing" />}
                   onRowClick={(r) => opened.push(r.id)} rowLabel={(r) => `Open ${r.name}`}
                   columns={[{ key: "n", header: "Name", width: "10rem", cell: (r) => r.name }]} />
      </>
    );
  }
  const { container } = mount(<List />);
  expect(container.querySelectorAll("[data-slot=skeleton]").length).toBeGreaterThan(0);
  await userEvent.click(screen.getByRole("button", { name: "Load" }));
  const cell = screen.getByText("A very long name");
  expect(cell).toHaveAttribute("title", "A very long name");
  await userEvent.click(cell);
  screen.getByRole("row", { name: "Open A very long name" }).focus();
  await userEvent.keyboard("{Enter}");
  expect(opened).toEqual(["a", "a"]);
});

it("shows the empty state, and pages only when there is more than one page", async () => {
  const onPage = vi.fn();
  const { rerender } = render(<>
    <DataTable rows={[]} rowKey={() => ""} empty={<EmptyState title="No rows">Add one.</EmptyState>} columns={[]} />
    <Pager page={0} size={50} count={3} onPage={onPage} />
  </>);
  expect(screen.getByText("No rows")).toBeInTheDocument();
  expect(screen.queryByRole("navigation", { name: "Pages" })).not.toBeInTheDocument();
  rerender(<Pager page={1} size={50} count={50} onPage={onPage} />);
  await userEvent.click(screen.getByRole("button", { name: "Previous" }));
  await userEvent.click(screen.getByRole("button", { name: "Next" }));
  expect(onPage.mock.calls).toEqual([[0], [2]]);
});

it("lays out the page header, details and errors", async () => {
  const retry = vi.fn();
  render(<>
    <PageHeader title="Customers" site="DLF Meadows" description="Find a customer." actions={<button type="button">Add</button>} />
    <DetailList items={[{ label: "Flat", value: "" }, { label: "Mobile", value: "98" }]} />
    <ErrorState message="Cannot reach the server." onRetry={retry} />
  </>);
  expect(screen.getByRole("heading", { name: "Customers" })).toBeInTheDocument();
  expect(screen.getByText("DLF Meadows")).toBeInTheDocument();
  expect(screen.getByText("Flat").nextSibling).toHaveTextContent("-");
  await userEvent.click(screen.getByRole("button", { name: "Try again" }));
  expect(retry).toHaveBeenCalled();
});

it("counts a pager's pages when the total is known, and stops at the last page", async () => {
  const onPage = vi.fn();
  const { rerender } = render(<Pager page={0} size={50} count={50} total={120} onPage={onPage} />);
  expect(screen.getByText("1-50 of 120 · Page 1 of 3")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
  rerender(<Pager page={2} size={50} count={20} total={120} onPage={onPage} />);
  expect(screen.getByText("101-120 of 120 · Page 3 of 3")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  rerender(<Pager page={0} size={50} count={0} total={0} onPage={onPage} />);
  expect(screen.queryByRole("navigation", { name: "Pages" })).not.toBeInTheDocument();
});

it("shows a headline number, or a dash while it loads", () => {
  render(<><StatTile label="Total" value={12} hint="All" /><StatTile label="Waiting" value={5} loading /></>);
  expect(screen.getByText("12")).toBeInTheDocument();
  expect(screen.getByText("All")).toBeInTheDocument();
  expect(screen.queryByText("5")).not.toBeInTheDocument();
  expect(screen.getByText("–")).toBeInTheDocument();
});

it("makes a summary tile a button that reports its selection", async () => {
  const onSelect = vi.fn();
  render(<StatTile label="Active" value={3} selected onSelect={onSelect} />);
  const tile = screen.getByRole("button", { name: "Active: 3" });
  expect(tile).toHaveAttribute("aria-pressed", "true");
  await userEvent.click(tile);
  expect(onSelect).toHaveBeenCalledTimes(1);
});

it("switches a table to tiles, opens a tile, and remembers the choice", async () => {
  const open = vi.fn();
  function Demo() {
    const [view, setView] = useViewMode("demo");
    return (
      <>
        <ViewToggle value={view} onChange={setView} />
        <DataTable view={view} rows={[{ id: "a", n: "One" }]} rowKey={(r) => r.id} empty={<p>none</p>}
                   onRowClick={open} rowLabel={(r) => `Open ${r.n}`} renderTile={(r) => <span>{r.n} tile</span>}
                   columns={[{ key: "n", header: "Name", cell: (r) => r.n }]} />
      </>
    );
  }
  const { unmount } = render(<Demo />);
  expect(screen.getByRole("table")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "List" })).toHaveAttribute("aria-pressed", "true");
  await userEvent.click(screen.getByRole("button", { name: "Tiles" }));
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Open One" }));
  expect(open).toHaveBeenCalledWith({ id: "a", n: "One" });
  expect(localStorage.getItem("priveo.view.demo")).toBe("tiles");
  unmount();
  render(<Demo />);
  expect(screen.queryByRole("table")).not.toBeInTheDocument();
  expect(screen.getByText("One tile")).toBeInTheDocument();
  localStorage.removeItem("priveo.view.demo");
});

it("shows the empty state and skeleton tiles in the tile view", () => {
  const { rerender } = render(<DataTable view="tiles" rows={undefined} loading rowKey={() => ""} empty={<p>none</p>}
                                         renderTile={() => null} columns={[]} />);
  expect(screen.queryByText("none")).not.toBeInTheDocument();
  rerender(<DataTable view="tiles" rows={[]} rowKey={() => ""} empty={<p>none</p>} renderTile={() => null} columns={[]} />);
  expect(screen.getByText("none")).toBeInTheDocument();
});

it("keeps a table as wide as its columns need, so a narrow screen scrolls instead of squeezing", () => {
  render(
    <DataTable rows={[{ id: "a" }]} rowKey={(r) => r.id} empty={<p>none</p>} columns={[
      { key: "a", header: "A", width: "10rem", cell: () => "x" },
      { key: "b", header: "B", width: "25%", cell: () => "y" },
      { key: "c", header: "C", cell: () => "z" },
    ]} />,
  );
  // The 25% column needs 8 rem of its own, so the table is 32 rem; the others fit in the other 75%.
  expect(screen.getByRole("table")).toHaveStyle({ minWidth: "32rem" });
  expect(tableMinRem(["10rem", "25%", undefined])).toBe(32);
  expect(tableMinRem(["10rem", "7rem", undefined])).toBe(25);
});

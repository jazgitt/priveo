import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider } from "../../components";
import { CrewDetailPage } from "./CrewDetailPage";
import { CrewListPage } from "./CrewListPage";
import { hoursBody, defaultHours } from "./api";

const fetchMock = vi.fn();

function json(status: number, body?: unknown) {
  return new Response(body === undefined ? null : JSON.stringify(body), { status });
}
const err = (status: number, code: string, message: string) =>
  json(status, { code, message, fields: {}, request_id: "" });

const hours = defaultHours();
const raj = {
  id: "c1", name: "Raj Kumar", mobile: "9000000001", society_id: "s1", society: "Lake View",
  role: "Member", active: true, locked: false, working_hours: hours,
  paired_member_id: null, paired_member: "", exceptions: [],
};
const asha = { ...raj, id: "c2", name: "Asha Devi", mobile: "9000000002", role: "Trainee",
               paired_member_id: "c1", paired_member: "Raj Kumar" };
const societies = [{ id: "s1", name: "Lake View", active: true }, { id: "s2", name: "Park", active: true }];

function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ToastProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/crew" element={<CrewListPage />} />
            <Route path="/crew/:id" element={<CrewDetailPage />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

const openTab = async (name: string) =>
  userEvent.click(await screen.findByRole("tab", { name }));

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("crew list", () => {
  it("filters by role and search, and asks the API for a society", async () => {
    fetchMock.mockImplementation(async (p: string) => {
      if (p.startsWith("/v1/admin/directory/societies")) return json(200, societies);
      if (p.startsWith("/v1/admin/crew")) return json(200, [raj, asha]);
      return err(404, "not_found", "no");
    });
    renderAt("/crew");
    expect(await screen.findByText("Raj Kumar")).toBeInTheDocument();
    expect(screen.getByText("Asha Devi")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Role"), "Trainee");
    expect(screen.queryByText("Raj Kumar")).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Role"), "");
    await userEvent.type(screen.getByLabelText("Search"), "9000000001");
    expect(screen.queryByText("Asha Devi")).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Society"), "s1");
    await waitFor(() => expect(fetchMock.mock.calls.some(
      (c) => c[0] === "/v1/admin/crew?society_id=s1")).toBe(true));
  });

  it("onboards a Trainee with a paired Member and shows the password once", async () => {
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) => {
      if (p.startsWith("/v1/admin/directory/societies")) return json(200, societies);
      if (p === "/v1/admin/crew" && init?.method === "POST") {
        return json(201, { crew: { ...asha, name: "Sam Lee" }, login_id: "9000000009", password: "Sam4821$" });
      }
      if (p.startsWith("/v1/admin/crew")) return json(200, [raj]);
      return err(404, "not_found", "no");
    });
    renderAt("/crew");
    await userEvent.click(await screen.findByRole("button", { name: "Onboard crew" }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Name"), "Sam Lee");
    await userEvent.type(within(dialog).getByLabelText("Mobile number"), "9000000009");
    await userEvent.selectOptions(within(dialog).getByLabelText("Society"), "s1");
    await userEvent.selectOptions(within(dialog).getByLabelText("Role"), "Trainee");
    const save = within(dialog).getByRole("button", { name: "Onboard" });
    expect(save).toBeDisabled();
    await userEvent.selectOptions(await within(dialog).findByLabelText("Paired Member"), "c1");
    await userEvent.click(save);
    expect(await screen.findByTestId("issued-password")).toHaveTextContent("Sam4821$");
    expect(screen.getByText(/shown once/)).toBeInTheDocument();
    const post = fetchMock.mock.calls.find((c) => c[1]?.method === "POST")!;
    const body = JSON.parse(post[1].body);
    expect(body).toMatchObject({ name: "Sam Lee", mobile: "9000000009", society_id: "s1",
                                 role: "Trainee", paired_member_id: "c1" });
    expect(body.working_hours).toHaveLength(7);
    await userEvent.click(screen.getByRole("button", { name: "I have noted it" }));
    expect(screen.queryByTestId("issued-password")).not.toBeInTheDocument();
  });
});

describe("crew detail", () => {
  function detailMock(extra: (p: string, init?: RequestInit) => Response | undefined) {
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) => {
      const r = extra(p, init);
      if (r) return r;
      if (p === "/v1/admin/crew/c1") return json(200, raj);
      if (p === "/v1/admin/crew?society_id=s1") return json(200, [raj, asha]);
      if (p === "/v1/admin/crew/c1/sessions") {
        return json(200, [{ id: "x1", channel: "mobile",
                            device_name: "Crew Pixel", platform: "android", app_version: "1.2.3",
                            signed_in_at: "2026-10-10T05:00:00Z", last_active_at: "2026-10-11T06:30:00Z" }]);
      }
      return err(404, "not_found", "no");
    });
  }

  it("asks to release jobs when deactivation is blocked, then retries", async () => {
    let calls = 0;
    detailMock((p, init) => {
      if (p === "/v1/admin/crew/c1/deactivate" && init?.method === "POST") {
        calls += 1;
        return calls === 1
          ? err(409, "has_open_jobs", "This crew member holds 2 frozen jobs.")
          : json(200, { crew: { ...raj, active: false }, released_jobs: [
            { job_id: "j1", date: "2026-10-12", service: "Cleaning-External",
              vehicle_id: "v1", registration: "KA01AB1234" }] });
      }
      return undefined;
    });
    renderAt("/crew/c1");
    await openTab("Account");
    await userEvent.click(await screen.findByRole("button", { name: "Deactivate" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/holds 2 frozen jobs/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: /Send jobs to Needs scheduling/ }));
    expect(await screen.findByText(/KA01AB1234/)).toBeInTheDocument();
    const posts = fetchMock.mock.calls.filter((c) => c[0].endsWith("/deactivate"));
    expect(JSON.parse(posts[0][1].body)).toEqual({ release_jobs: false });
    expect(JSON.parse(posts[1][1].body)).toEqual({ release_jobs: true });
  });

  it("adds a Late start range with a start time", async () => {
    detailMock((p, init) => {
      if (p === "/v1/admin/crew/c1/exceptions" && init?.method === "POST") {
        return json(201, { crew: raj, exceptions: [], released_jobs: [] });
      }
      return undefined;
    });
    renderAt("/crew/c1");
    await openTab("Exceptions");
    await userEvent.selectOptions(await screen.findByLabelText("Type"), "Late start");
    await userEvent.type(screen.getByLabelText("From date"), "2026-10-20");
    await userEvent.type(screen.getByLabelText("To date"), "2026-10-22");
    await userEvent.type(screen.getByLabelText("Can start at"), "09:30");
    await userEvent.click(screen.getByRole("button", { name: "Add exception" }));
    await waitFor(() => {
      const post = fetchMock.mock.calls.find((c) => c[1]?.method === "POST")!;
      expect(JSON.parse(post[1].body)).toEqual({
        kind: "Late start", from_date: "2026-10-20", to_date: "2026-10-22", start: "09:30" });
    });
  });

  it("resets a password and shows it once, and signs a session out", async () => {
    detailMock((p, init) => {
      if (p === "/v1/admin/crew/c1/password" && init?.method === "POST") {
        return json(200, { crew: raj, login_id: "9000000001", password: "Raj1111$" });
      }
      if (p === "/v1/admin/crew/c1/sessions/x1/logout" && init?.method === "POST") {
        return json(200, { ended: 1 });
      }
      return undefined;
    });
    renderAt("/crew/c1");
    await openTab("Account");
    await userEvent.click(await screen.findByRole("button", { name: "Reset password" }));
    const confirm = await screen.findByRole("dialog");
    await userEvent.click(within(confirm).getByRole("button", { name: "Reset password" }));
    expect(await screen.findByTestId("issued-password")).toHaveTextContent("Raj1111$");
    await userEvent.click(screen.getByRole("button", { name: "I have noted it" }));
    await openTab("Sessions");
    expect(await screen.findByText("Crew Pixel")).toBeInTheDocument();
    expect(screen.getByText(/App 1.2.3/)).toBeInTheDocument();
    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(
      (c) => c[0] === "/v1/admin/crew/c1/sessions/x1/logout")).toBe(true));
  });

  it("changes a role to Trainee with a Member and lists released jobs", async () => {
    const bo = { ...raj, id: "c3", name: "Bo Lin", mobile: "9000000003" };
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) => {
      if (p === "/v1/admin/crew/c3") return json(200, bo);
      if (p === "/v1/admin/crew?society_id=s1") return json(200, [raj, bo]);
      if (p === "/v1/admin/crew/c3/sessions") return json(200, []);
      if (p === "/v1/admin/crew/c3/role" && init?.method === "PUT") {
        return json(200, { crew: { ...bo, role: "Trainee" }, released_jobs: [
          { job_id: "j9", date: "2026-10-13", service: "Deep Spa", vehicle_id: "v",
            registration: "KA09ZZ0001" }] });
      }
      return err(404, "not_found", "no");
    });
    renderAt("/crew/c3");
    await openTab("Role and pairing");
    await userEvent.selectOptions(await screen.findByLabelText("Role"), "Trainee");
    const change = screen.getByRole("button", { name: "Change role" });
    expect(change).toBeDisabled();
    await userEvent.selectOptions(screen.getByLabelText("Paired Member"), "c1");
    await userEvent.click(change);
    expect(await screen.findByText(/KA09ZZ0001/)).toBeInTheDocument();
    const put = fetchMock.mock.calls.find((c) => c[1]?.method === "PUT")!;
    expect(JSON.parse(put[1].body)).toEqual({ role: "Trainee", paired_member_id: "c1" });
  });
});

describe("hours helper", () => {
  it("clears start and end on a day off", () => {
    const h = defaultHours();
    h[6] = { ...h[6], working: false };
    expect(hoursBody(h)[6]).toEqual({ day: "Sunday", working: false, start: "", end: "" });
  });
});

describe("crew society over time", () => {
  const stay = (over: object) => ({ id: "a1", society_id: "s1", society: "Lake View",
    effective_from: "2026-09-01", effective_to: null, pending: false, ...over });

  it("shows the stays and sets a move from a date", async () => {
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) => {
      if (p === "/v1/admin/crew/c1/society" && init?.method === "POST") {
        return json(200, { crew: raj, released_jobs: [] });
      }
      if (p === "/v1/admin/crew/c1/society-history") return json(200, [stay({})]);
      if (p === "/v1/admin/crew/c1/sessions") return json(200, []);
      if (p.startsWith("/v1/admin/directory/societies")) return json(200, societies);
      if (p === "/v1/admin/crew/c1") return json(200, raj);
      if (p.startsWith("/v1/admin/crew")) return json(200, [raj]);
      return err(404, "not_found", "no");
    });
    renderAt("/crew/c1?tab=society");
    expect(await screen.findByText("now")).toBeInTheDocument(); // The current stay has no end.
    // A Member is told that their Trainees move with them.
    expect(screen.getByRole("note")).toHaveTextContent("their society is updated too");
    await userEvent.selectOptions(await screen.findByLabelText("Move to society"), "s2");
    const date = screen.getByLabelText("Starts on") as HTMLInputElement;
    await userEvent.clear(date);
    await userEvent.type(date, "2099-01-15");
    await userEvent.click(screen.getByRole("button", { name: "Move crew member" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(
      (c) => c[0] === "/v1/admin/crew/c1/society" && c[1]?.method === "POST")).toBe(true));
    const post = fetchMock.mock.calls.find((c) => c[0] === "/v1/admin/crew/c1/society")!;
    expect(JSON.parse(post[1].body)).toEqual({
      society_id: "s2", effective_from: "2099-01-15", paired_member_id: null });
  });

  it("shows a move that starts later and lets the admin cancel it", async () => {
    fetchMock.mockImplementation(async (p: string, init?: RequestInit) => {
      if (p === "/v1/admin/crew/c1/society-moves/a2" && init?.method === "DELETE") return json(200, raj);
      if (p === "/v1/admin/crew/c1/sessions") return json(200, []);
      if (p === "/v1/admin/crew/c1/society-history") {
        return json(200, [stay({ effective_to: "2099-01-14" }),
          stay({ id: "a2", society_id: "s2", society: "Park", effective_from: "2099-01-15", pending: true })]);
      }
      if (p.startsWith("/v1/admin/directory/societies")) return json(200, societies);
      if (p === "/v1/admin/crew/c1") return json(200, raj);
      if (p.startsWith("/v1/admin/crew")) return json(200, [raj]);
      return err(404, "not_found", "no");
    });
    renderAt("/crew/c1?tab=society");
    expect(await screen.findByText("Starts later")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Cancel the move to Park" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(
      (c) => c[0] === "/v1/admin/crew/c1/society-moves/a2" && c[1]?.method === "DELETE")).toBe(true));
  });
});

describe("crew page layout", () => {
  const mock = () => fetchMock.mockImplementation(async (p: string) => {
    if (p.startsWith("/v1/admin/directory/societies")) return json(200, societies);
    if (p === "/v1/admin/crew/c1") return json(200, raj);
    if (p === "/v1/admin/crew/c1/sessions") return json(200, []);
    if (p === "/v1/admin/crew/c1/society-history") return json(200, []);
    if (p.startsWith("/v1/admin/crew")) return json(200, [raj, asha]);
    return err(404, "not_found", "no");
  });

  it("gives each row an edit icon that opens the crew member", async () => {
    mock();
    renderAt("/crew");
    const edit = await screen.findByRole("link", { name: "Edit Raj Kumar" });
    expect(edit).toHaveAttribute("href", "/crew/c1");
    expect(screen.getByRole("link", { name: "Edit Asha Devi" })).toHaveAttribute("href", "/crew/c2");
  });

  it("shows the sections as tabs, one at a time, starting on Details", async () => {
    mock();
    renderAt("/crew/c1");
    const tabs = await screen.findAllByRole("tab");
    expect(tabs.map((t) => t.textContent)).toEqual([
      "Details", "Society", "Role and pairing", "Working hours", "Exceptions", "Account", "Sessions"]);
    expect(screen.getByRole("tab", { name: "Details" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByLabelText("Name")).toBeInTheDocument();
    expect(screen.queryByLabelText("Paired Member")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reset password" })).not.toBeInTheDocument();
    await openTab("Account");
    expect(screen.getByRole("tab", { name: "Account" })).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByRole("button", { name: "Reset password" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Name")).not.toBeInTheDocument();
  });

  it("opens the tab named in the address and moves between tabs with the arrow keys", async () => {
    mock();
    renderAt("/crew/c1?tab=hours");
    expect(await screen.findByRole("tab", { name: "Working hours" })).toHaveAttribute("aria-selected", "true");
    screen.getByRole("tab", { name: "Working hours" }).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Exceptions" })).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{Home}");
    expect(screen.getByRole("tab", { name: "Details" })).toHaveAttribute("aria-selected", "true");
  });

  it("falls back to Details for an unknown tab", async () => {
    mock();
    renderAt("/crew/c1?tab=nonsense");
    expect(await screen.findByRole("tab", { name: "Details" })).toHaveAttribute("aria-selected", "true");
  });
});

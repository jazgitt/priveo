import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AdminJob, Board } from "../api";
import { applyMovesToBoard, useBatchMove } from "./commit";
import { resetBoardSenderForTests } from "./sync";

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn(), loading: vi.fn(), warning: vi.fn() },
}));

const KEY = ["board", "id", "s1"];
const fetchMock = vi.fn();

function job(id: string, over: Partial<AdminJob> = {}): AdminJob {
  return {
    id, visit_id: "v" + id, schedule_id: "s1", schedule_status: "Frozen", date: "2026-11-10", vehicle_id: "x",
    registration: "KA" + id, vehicle: "Car", customer_name: "C", service: "Cleaning-External", status: "Scheduled",
    duration_minutes: 30, crew_id: "c1", crew_name: "Asha", start_minute: 600, start_time: "10:00", end_time: "10:30",
    finish_by: null, late: false, manual: false, reason: "", ...over,
  };
}

const board = (): Board => ({
  schedule: { id: "s1", society_id: "soc", society_name: "S", start_date: "2026-11-10", end_date: "2026-11-10",
    status: "Draft", frozen_at: null, freeze_deadline: "2026-11-09T00:00:00Z" },
  days: [],
  crew: [
    { id: "c1", name: "Asha", role: "Member", start_minute: 480, end_minute: 1020 },
    { id: "c2", name: "Ravi", role: "Member", start_minute: 480, end_minute: 1020 },
  ],
  jobs: [job("j1"), job("j2", { start_minute: 660, start_time: "11:00", end_time: "11:30" })],
});

let qc: QueryClient;
const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={qc}>{children}</QueryClientProvider>;

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  vi.stubGlobal("BroadcastChannel", undefined);
  resetBoardSenderForTests();
  qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  qc.setQueryData(KEY, board());
  vi.mocked(toast.error).mockClear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("applyMovesToBoard (the optimistic view)", () => {
  it("shows a moved job on its new crew at its new time, marked By hand", () => {
    const out = applyMovesToBoard(board(), [{ job_id: "j1", crew_id: "c2", start_minute: 540 }]);
    const moved = out.jobs.find((j) => j.id === "j1")!;
    expect(moved.crew_id).toBe("c2");
    expect(moved.crew_name).toBe("Ravi");
    expect(moved.start_minute).toBe(540);
    expect(moved.start_time).toBe("09:00");
    expect(moved.end_time).toBe("09:30");
    expect(moved.manual).toBe(true);
    expect(out.jobs.find((j) => j.id === "j2")!.start_minute).toBe(660);
  });

  it("takes a job with a null crew off the board into Unscheduled", () => {
    const out = applyMovesToBoard(board(), [{ job_id: "j1", crew_id: null, start_minute: null }]);
    const moved = out.jobs.find((j) => j.id === "j1")!;
    expect(moved.crew_id).toBeNull();
    expect(moved.crew_name).toBeNull();
    expect(moved.start_minute).toBeNull();
    expect(moved.start_time).toBeNull();
  });
});

describe("useBatchMove", () => {
  it("shows the move at once and keeps it when the server saves it", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ jobs: [], warnings: [] }), { status: 200 }));
    const onResult = vi.fn();
    const { result } = renderHook(() => useBatchMove(KEY, onResult), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ moves: [{ job_id: "j1", crew_id: "c2", start_minute: 540 }] });
    });
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/v1/admin/scheduling/jobs/batch-move");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ moves: [{ job_id: "j1", crew_id: "c2", start_minute: 540 }], override: false });
    expect(onResult).toHaveBeenCalledWith({ jobs: [], warnings: [] });
    expect(qc.getQueryData<Board>(KEY)!.jobs[0].crew_id).toBe("c2");
  });

  it("rolls the board back and says why when the server refuses an overlap", async () => {
    let answer!: (r: Response) => void;
    fetchMock.mockImplementation(() => new Promise<Response>((resolve) => { answer = resolve; }));
    const before = qc.getQueryData<Board>(KEY);
    const { result } = renderHook(() => useBatchMove(KEY), { wrapper });

    let failed: unknown = null;
    const pending = result.current.mutateAsync({
      moves: [{ job_id: "j1", crew_id: "c2", start_minute: 660 }, { job_id: "j2", crew_id: "c2", start_minute: 720 }],
    }).catch((e: unknown) => { failed = e; });

    // While the server is thinking, the card already shows at its new place.
    await waitFor(() => expect(qc.getQueryData<Board>(KEY)!.jobs[0].crew_id).toBe("c2"));

    answer(new Response(JSON.stringify({
      code: "overlap", message: "KA02 is in the way at 11:00-11:30. Please try another time.", fields: {}, request_id: "r1",
    }), { status: 409 }));
    await act(async () => { await pending; });

    // Nothing moved: the whole batch is refused, so the board is the one from before.
    expect(qc.getQueryData<Board>(KEY)).toEqual(before);
    expect(failed).toBeTruthy();
    expect((failed as { status?: number }).status).toBe(409);
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      "KA02 is in the way at 11:00-11:30. Please try another time.",
      expect.objectContaining({ duration: 8000 }),
    );
  });

  it("shows the overlap text when the 409 body has no usable message", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ detail: { code: "overlap", job_ids: ["j1"] } }), { status: 409 }));
    const before = qc.getQueryData<Board>(KEY);
    const { result } = renderHook(() => useBatchMove(KEY), { wrapper });
    await act(async () => {
      await result.current.mutateAsync({ moves: [{ job_id: "j1", crew_id: "c2", start_minute: 660 }] }).catch(() => {});
    });
    expect(qc.getQueryData<Board>(KEY)).toEqual(before);
    expect(vi.mocked(toast.error).mock.calls[0][0]).toMatch(/overlaps another job/);
  });
});

describe("the optimistic card matches what the server answers", () => {
  it("marks a placed card by hand and locked, with no reason, so the refetch changes nothing on it", () => {
    const out = applyMovesToBoard(board(), [{ job_id: "j1", crew_id: "c2", start_minute: 540 }]);
    const j = out.jobs.find((x) => x.id === "j1")!;
    expect(j).toMatchObject({ manual: true, placed_by_hand: true, hand_locked: true, reason: "" });
  });

  it("shows a taken-off card with the lock icon and its reason, keeping its lock state", () => {
    const b = board();
    b.jobs[0] = job("j1", { hand_locked: false });
    const j = applyMovesToBoard(b, [{ job_id: "j1", crew_id: null, start_minute: null }]).jobs[0];
    expect(j).toMatchObject({ crew_id: null, placed_by_hand: true, hand_locked: false, reason: "Taken off the schedule by the admin." });
  });

  it("leaves the cards it shifts unlocked", () => {
    const out = applyMovesToBoard(board(), [
      { job_id: "j1", crew_id: "c1", start_minute: 540 }, { job_id: "j2", crew_id: "c1", start_minute: 600 }]);
    expect(out.jobs.find((x) => x.id === "j2")!.hand_locked).toBeFalsy();
  });
});


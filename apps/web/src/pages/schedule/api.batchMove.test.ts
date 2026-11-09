import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import { batchMoveJobs } from "./api";

const fetchMock = vi.fn();
beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => {
  fetchMock.mockReset();
  vi.unstubAllGlobals();
});

describe("batchMoveJobs (pinned batch-move contract)", () => {
  it("posts every move in one request with the override flag", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({
      jobs: [], warnings: [{ job_id: "j2", code: "crew_hours", message: "Runs past the crew member's hours." }],
    }), { status: 200 }));

    const out = await batchMoveJobs([
      { job_id: "j1", crew_id: "c1", start_minute: 600 },
      { job_id: "j2", crew_id: "c1", start_minute: 630 },
    ], false);

    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/v1/admin/scheduling/jobs/batch-move");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      moves: [
        { job_id: "j1", crew_id: "c1", start_minute: 600 },
        { job_id: "j2", crew_id: "c1", start_minute: 630 },
      ],
      override: false,
    });
    expect(out.warnings).toHaveLength(1);
    expect(out.warnings[0].code).toBe("crew_hours");
  });

  it("sends a null crew to take a job to Unscheduled", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ jobs: [], warnings: [] }), { status: 200 }));
    await batchMoveJobs([{ job_id: "j1", crew_id: null, start_minute: null }], true);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toEqual({
      moves: [{ job_id: "j1", crew_id: null, start_minute: null }],
      override: true,
    });
  });

  it("turns a 409 without a usable message into the overlap text", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ detail: { code: "overlap", job_ids: ["j1"] } }), { status: 409 }));
    const err = await batchMoveJobs([{ job_id: "j1", crew_id: "c1", start_minute: 600 }], false).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(409);
    expect((err as ApiError).code).toBe("overlap");
    expect((err as ApiError).message).toMatch(/overlaps another job/);
  });

  it("keeps the server's own overlap message when it sends one", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({
      code: "overlap", message: "KA09 is in the way at 10:00-10:30.", fields: {}, request_id: "r",
    }), { status: 409 }));
    const err = await batchMoveJobs([{ job_id: "j1", crew_id: "c1", start_minute: 600 }], false).catch((e: unknown) => e);
    expect((err as ApiError).message).toBe("KA09 is in the way at 10:00-10:30.");
  });
});

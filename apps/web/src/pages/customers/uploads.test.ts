import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { browserUploadHeaders, uploadCustomerAsset } from "./api";

const fetchMock = vi.fn();
const reply = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals(); });

// What the API hands out when the store is Vercel Blob.
const BLOB_HEADERS = {
  authorization: "Bearer vercel_blob_client_x", "x-api-version": "13", "x-vercel-blob-access": "public",
  "x-content-type": "image/jpeg", "x-add-random-suffix": "0", "x-allow-overwrite": "1",
};

describe("customer uploads from the browser", () => {
  it("leaves out the headers Vercel Blob's CORS reply does not allow", () => {
    expect(browserUploadHeaders(BLOB_HEADERS)).toEqual({
      authorization: "Bearer vercel_blob_client_x", "x-api-version": "13", "x-vercel-blob-access": "public",
      "x-content-type": "image/jpeg",
    });
    expect(browserUploadHeaders({ "Content-Type": "image/png" })).toEqual({ "Content-Type": "image/png" });
  });

  it("sends the file to the signed address with only the allowed headers, then confirms it", async () => {
    fetchMock.mockImplementation(async (path: string, init?: RequestInit) => {
      if (path === "/v1/admin/customer-uploads") {
        return reply({ id: "u1", upload_url: "https://vercel.com/api/blob/?pathname=a.jpg", method: "PUT", headers: BLOB_HEADERS }, 201);
      }
      if (path.startsWith("https://vercel.com/")) return reply({ url: "https://x/a.jpg" });
      if (path === "/v1/admin/customer-uploads/u1/confirm" && init?.method === "POST") return reply({ id: "u1", url: "https://x/a.jpg" });
      return reply({}, 404);
    });
    const file = new File(["x"], "car.jpg", { type: "image/jpeg" });
    await expect(uploadCustomerAsset(file, "vehicle")).resolves.toEqual({ id: "u1", url: "https://x/a.jpg" });
    const put = fetchMock.mock.calls.find((c) => String(c[0]).startsWith("https://vercel.com/"))!;
    expect(put[1].method).toBe("PUT");
    expect(Object.keys(put[1].headers)).not.toContain("x-add-random-suffix");
    expect(Object.keys(put[1].headers)).not.toContain("x-allow-overwrite");
    expect(put[1].headers.authorization).toBe("Bearer vercel_blob_client_x");
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { browserUploadHeaders, fileProblem, fileType, keepForSite, uploadCustomerAsset } from "./api";

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
    await expect(uploadCustomerAsset(file)).resolves.toEqual({ id: "u1", url: "https://x/a.jpg" });
    const put = fetchMock.mock.calls.find((c) => String(c[0]).startsWith("https://vercel.com/"))!;
    expect(put[1].method).toBe("PUT");
    expect(Object.keys(put[1].headers)).not.toContain("x-add-random-suffix");
    expect(Object.keys(put[1].headers)).not.toContain("x-allow-overwrite");
    expect(put[1].headers.authorization).toBe("Bearer vercel_blob_client_x");
  });
});

describe("what is checked before a file is sent", () => {
  it("reads the type from the extension when the browser leaves it empty (HEIC on Windows)", () => {
    expect(fileType(new File(["x"], "IMG_1.HEIC", { type: "" }))).toBe("image/heic");
    expect(fileType(new File(["x"], "a.jpg", { type: "image/png" }))).toBe("image/png");
    expect(fileType(new File(["x"], "a.bin", { type: "" }))).toBe("");
  });

  it("refuses the wrong format, an empty file and one that is too large, in plain words", () => {
    expect(fileProblem(new File(["x"], "a.heic", { type: "" }))).toBeNull();
    expect(fileProblem(new File(["x"], "a.pdf", { type: "application/pdf" }))).toMatch(/JPG, PNG, HEIC or WebP/);
    expect(fileProblem(new File([], "a.jpg", { type: "image/jpeg" }))).toBe("That file is empty.");
    const big = (n: number) => new File([new Uint8Array(n)], "a.jpg", { type: "image/jpeg" });
    expect(fileProblem(big(10 * 1024 * 1024))).toBe("The photo must be under 10 MB.");
    expect(fileProblem(big(10 * 1024 * 1024 - 1))).toBeNull();
  });

  it("sends the extension-derived type to the API and sends nothing for a refused file", async () => {
    fetchMock.mockImplementation(async (path: string) => {
      if (path === "/v1/admin/customer-uploads") return reply({ id: "u1", upload_url: "/media", method: "PUT", headers: {} }, 201);
      if (path === "/media") return reply({});
      return reply({ id: "u1", url: "https://x/a.heic" });
    });
    await uploadCustomerAsset(new File(["x"], "car.heic", { type: "" }));
    const first = fetchMock.mock.calls.find((c) => c[0] === "/v1/admin/customer-uploads")!;
    expect(JSON.parse(first[1].body)).toMatchObject({ content_type: "image/heic", purpose: "vehicle" });
    fetchMock.mockClear();
    await expect(uploadCustomerAsset(new File(["x"], "n.txt", { type: "text/plain" }))).rejects.toThrow(/Choose a JPG/);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("keeping numbers on screen while a list reloads", () => {
  it("keeps the last data for a search or tab change, but not when the site changes", () => {
    const key = (site: string) => ({ queryKey: ["customers", "summary", "", site] });
    expect(keepForSite("s1")({ total: 1 }, key("s1"))).toEqual({ total: 1 });
    expect(keepForSite("s2")({ total: 1 }, key("s1"))).toBeUndefined();
    expect(keepForSite("s1")(undefined, undefined)).toBeUndefined();
  });
});

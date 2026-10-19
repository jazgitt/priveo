// The API client. The portal and the API share one origin, so a call is a
// plain same-origin fetch: the browser adds the httpOnly session cookie, and
// this file adds the CSRF header on every call that changes data.

import { track } from "../analytics/analytics";

const CSRF_COOKIE = "priveo_csrf";
const SAFE = new Set(["GET", "HEAD", "OPTIONS"]);

/** The API's error envelope: { code, message, fields, request_id }. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: Record<string, string>;
  readonly requestId: string;

  constructor(status: number, code: string, message: string,
              fields: Record<string, string> = {}, requestId = "") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
    this.requestId = requestId;
  }
}

export function readCookie(name: string, source: string = document.cookie): string | null {
  for (const part of source.split(";")) {
    const [k, ...rest] = part.trim().split("=");
    if (k === name) return decodeURIComponent(rest.join("="));
  }
  return null;
}

type Listener = () => void;
let onUnauthorized: Listener | null = null;

/** Called when a signed-in call comes back 401, so the app can show sign-in. */
export function setUnauthorizedListener(fn: Listener | null): void {
  onUnauthorized = fn;
}

export interface RequestOptions {
  method?: string;
  body?: unknown;
  signal?: AbortSignal;
  /** A 401 here is an answer (wrong password, no session), not a lost session. */
  quiet401?: boolean;
}

async function toError(res: Response): Promise<ApiError> {
  try {
    const b = await res.json();
    if (b && typeof b.code === "string") {
      return new ApiError(res.status, b.code, String(b.message ?? ""), b.fields ?? {},
                          String(b.request_id ?? ""));
    }
  } catch {
    // Not JSON: fall through to the generic error.
  }
  return new ApiError(res.status, "http_error", "Something went wrong. Please try again.");
}

export async function api<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const method = (opts.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = { Accept: "application/json" };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (!SAFE.has(method)) {
    const csrf = readCookie(CSRF_COOKIE);
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  let res: Response;
  try {
    res = await fetch(path, {
      method,
      headers,
      credentials: "same-origin",
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
      signal: opts.signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    track("api error", { status: 0, code: "network_error" });
    throw new ApiError(0, "network_error", "Cannot reach the server. Check the connection.");
  }

  if (!res.ok) {
    const err = await toError(res);
    // Server faults only, and never the message or fields: they can name a customer.
    if (res.status >= 500) track("api error", { status: err.status, code: err.code, request_id: err.requestId });
    if (res.status === 401 && !opts.quiet401) onUnauthorized?.();
    throw err;
  }
  if (res.status === 204) return undefined as T;
  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError(res.status, "bad_response", "The server sent an unexpected reply.");
  }
}

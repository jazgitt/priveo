import type { CaptureResult } from "posthog-js";
import { beforeEach, describe, expect, it, vi } from "vitest";

const ph = vi.hoisted(() => ({
  init: vi.fn(), capture: vi.fn(), identify: vi.fn(), reset: vi.fn(), register: vi.fn(),
}));
vi.mock("posthog-js", () => ({ default: ph }));

import {
  analyticsActive, cleanEvent, identifyUser, initAnalytics, resetAnalyticsForTests,
  resetUser, scrubUrl, track,
} from "./analytics";

const flush = () => new Promise((r) => setTimeout(r, 0));

beforeEach(() => {
  resetAnalyticsForTests();
  Object.values(ph).forEach((f) => f.mockClear());
});

describe("scrubUrl", () => {
  it("drops the query and fragment and replaces record ids", () => {
    expect(scrubUrl("/portal/customers/123e4567-e89b-12d3-a456-426614174000?tab=a#x"))
      .toBe("/portal/customers/:id");
    expect(scrubUrl("https://h/portal/payments/42/pay")).toBe("https://h/portal/payments/:id/pay");
    expect(scrubUrl("/portal/settings")).toBe("/portal/settings");
  });
});

describe("cleanEvent", () => {
  it("scrubs urls and removes personal properties", () => {
    const e = {
      uuid: "u", event: "x",
      properties: {
        $current_url: "https://h/portal/customers/42?q=Aarav", $pathname: "/portal/customers/42",
        email: "a@b.c", Mobile: "9000000000", display_name: "Aarav", role: "admin",
      },
    } as unknown as CaptureResult;
    const out = cleanEvent(e)!.properties as Record<string, unknown>;
    expect(out.$current_url).toBe("https://h/portal/customers/:id");
    expect(out.$pathname).toBe("/portal/customers/:id");
    expect(out).not.toHaveProperty("email");
    expect(out).not.toHaveProperty("Mobile");
    expect(out).not.toHaveProperty("display_name");
    expect(out.role).toBe("admin");
  });

  it("passes null through", () => {
    expect(cleanEvent(null)).toBeNull();
  });
});

describe("without a key", () => {
  it("does nothing and loads nothing", async () => {
    initAnalytics({ key: "", host: "", replay: false });
    track("customer or vehicle added");
    identifyUser("u1", "admin");
    resetUser();
    await flush();
    expect(analyticsActive()).toBe(false);
    expect(ph.init).not.toHaveBeenCalled();
    expect(ph.capture).not.toHaveBeenCalled();
  });
});

describe("with a key", () => {
  it("starts with replay off and sends queued calls once ready", async () => {
    initAnalytics({ key: "phc_test", host: "", replay: false });
    track("setting saved", { n: 1 });
    identifyUser("u1", "admin");
    await flush();

    expect(analyticsActive()).toBe(true);
    const [key, cfg] = ph.init.mock.calls[0];
    expect(key).toBe("phc_test");
    expect(cfg.api_host).toBe("https://eu.i.posthog.com");
    expect(cfg.autocapture).toBe(false);
    expect(cfg.disable_session_recording).toBe(true);
    // Nothing is masked or blocked for now, except password fields.
    expect(cfg.mask_all_text).toBe(false);
    expect(cfg.session_recording.maskAllInputs).toBe(false);
    expect(cfg.session_recording.maskInputOptions).toEqual({ password: true });
    expect(cfg.session_recording.maskTextSelector).toBeUndefined();
    expect(cfg.session_recording.blockSelector).toBeUndefined();
    // Bodies stay off: the sign-in body holds the password.
    expect(cfg.session_recording.recordBody).toBe(false);
    expect(cfg.session_recording.recordHeaders).toBe(false);
    cfg.loaded({ register: ph.register });
    expect(ph.register).toHaveBeenCalledWith({ platform: "web-portal" });
    expect(ph.capture).toHaveBeenCalledWith("setting saved", { n: 1 });
    expect(ph.identify).toHaveBeenCalledWith("u1", { role: "admin" });
  });

  it("turns replay on only when asked", async () => {
    initAnalytics({ key: "phc_test", host: "https://eu.i.posthog.com", replay: true });
    await flush();
    expect(ph.init.mock.calls[0][1].disable_session_recording).toBe(false);
  });

  it("resets only after someone was identified", async () => {
    initAnalytics({ key: "phc_test", host: "", replay: false });
    await flush();
    resetUser();
    expect(ph.reset).not.toHaveBeenCalled();
    identifyUser("u1", "admin");
    resetUser();
    expect(ph.reset).toHaveBeenCalledTimes(1);
  });

  it("ignores a second init", async () => {
    initAnalytics({ key: "phc_test", host: "", replay: false });
    initAnalytics({ key: "phc_other", host: "", replay: false });
    await flush();
    expect(ph.init).toHaveBeenCalledTimes(1);
  });
});

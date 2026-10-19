// Product analytics (PostHog, EU). This is the only file that knows the
// vendor. Without a key nothing loads and every call does nothing. Event
// properties never carry a name, mobile number, email or address. A recording,
// for now, masks nothing: it shows every screen as it is. What to mask is still
// to be decided. Password fields stay hidden, as the library always does.
import type { CaptureResult, PostHog } from "posthog-js";

export interface AnalyticsConfig {
  /** The PostHog project key. Empty turns analytics off. */
  key: string;
  host: string;
  /** Session replay. Off unless this is true. */
  replay: boolean;
}

export const DEFAULT_HOST = "https://eu.i.posthog.com";
const UI_HOST = "https://eu.posthog.com";

/** Property names that must never leave the browser. */
const PERSONAL_KEYS = /^(email|mobile|phone|name|display_name|full_name|address|vehicle_number)$/i;
const URL_KEYS = ["$current_url", "$pathname", "$referrer", "$initial_referrer"];
const UUID = /[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/g;

/** A URL or path without its query, fragment or record ids. */
export function scrubUrl(url: string): string {
  return url.split(/[?#]/)[0].replace(UUID, ":id").replace(/\/\d+(?=\/|$)/g, "/:id");
}

/** The before-send step: scrubs URLs and drops any personal property. */
export function cleanEvent(e: CaptureResult | null): CaptureResult | null {
  if (!e) return e;
  const props = e.properties as Record<string, unknown> | undefined;
  if (props) {
    for (const k of Object.keys(props)) {
      if (PERSONAL_KEYS.test(k)) delete props[k];
    }
    for (const k of URL_KEYS) {
      if (typeof props[k] === "string") props[k] = scrubUrl(props[k] as string);
    }
  }
  return e;
}

let ph: PostHog | null = null;
let enabled = false;
let identified = false;
let queue: Array<(p: PostHog) => void> = [];

function whenReady(fn: (p: PostHog) => void): void {
  if (ph) fn(ph);
  else if (enabled) queue.push(fn);
}

export function analyticsActive(): boolean {
  return enabled;
}

/** Starts PostHog in the background. Safe to call once, before the first render. */
export function initAnalytics(cfg: AnalyticsConfig): void {
  if (!cfg.key || enabled) return;
  enabled = true;
  void import("posthog-js").then(({ default: posthog }) => {
    posthog.init(cfg.key, {
      api_host: cfg.host || DEFAULT_HOST,
      ui_host: UI_HOST,
      person_profiles: "identified_only",
      // Page views come from history changes. Autocapture stays off: explicit
      // events are cleaner.
      capture_pageview: "history_change",
      capture_pageleave: false,
      autocapture: false,
      capture_exceptions: false,
      mask_all_text: false,
      mask_all_element_attributes: false,
      persistence: "localStorage+cookie",
      disable_session_recording: !cfg.replay,
      session_recording: {
        // Nothing is masked or blocked, except password fields.
        maskAllInputs: false,
        maskInputOptions: { password: true },
        // Request and response bodies stay off: the sign-in body holds the password.
        recordHeaders: false,
        recordBody: false,
      },
      before_send: cleanEvent,
      loaded: (p) => p.register({ platform: "web-portal" }),
    });
    ph = posthog;
    const waiting = queue;
    queue = [];
    waiting.forEach((fn) => fn(posthog));
  });
}

/** Names a thing that happened. Properties must hold no personal data. */
export function track(event: string, properties?: Record<string, string | number | boolean>): void {
  whenReady((p) => p.capture(event, properties));
}

/** Links events to the signed-in user by id and role only. */
export function identifyUser(userId: string, role: string): void {
  identified = true;
  whenReady((p) => p.identify(userId, { role }));
}

/** Forgets the user. Does nothing if nobody was identified. */
export function resetUser(): void {
  if (!identified) return;
  identified = false;
  whenReady((p) => p.reset());
}

/** Test helper: back to the state before init. */
export function resetAnalyticsForTests(): void {
  ph = null;
  enabled = false;
  identified = false;
  queue = [];
}

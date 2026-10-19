/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** PostHog project key. Set at build time. Empty turns analytics off. */
  readonly VITE_POSTHOG_KEY?: string;
  readonly VITE_POSTHOG_HOST?: string;
  /** "true" turns session replay on. */
  readonly VITE_POSTHOG_REPLAY?: string;
}

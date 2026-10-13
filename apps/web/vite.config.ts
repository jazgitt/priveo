import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The API target for `npm run dev`. The portal is served by the API in
// production, so in dev every /v1 call is proxied to the same address.
interface ProxyLike {
  on(
    event: "proxyRes",
    fn: (res: { headers: { "set-cookie"?: string[] } }) => void,
  ): void;
}

const api = process.env.VITE_API_TARGET ?? "http://localhost:8000";

export default defineConfig({
  // The portal lives under /portal/ on the API's origin.
  base: "/portal/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/v1": {
        target: api,
        changeOrigin: true,
        // The API marks its cookies Secure. Plain http://localhost would drop
        // them in some browsers, so dev strips the flag.
        configure: (proxy: ProxyLike) => {
          proxy.on("proxyRes", (res) => {
            const cookies = res.headers["set-cookie"];
            if (cookies) {
              res.headers["set-cookie"] = cookies.map((c) => c.replace(/;\s*secure/i, ""));
            }
          });
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.test.*", "src/test/**"],
      reporter: ["text", "json", "json-summary", "html"],
      thresholds: { lines: 90 },
    },
  },
});

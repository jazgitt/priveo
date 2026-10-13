# Priveo admin web portal

React + TypeScript + Vite. Served at `/portal/` on the same origin as the API, so sign-in is a cookie session with a CSRF header (no CORS).

Run these from `apps/web`.

| Command | What it does |
| --- | --- |
| `npm ci` | Install the locked dependencies. |
| `npm run dev` | Dev server on http://localhost:5173/portal/. `/v1/*` is proxied to `VITE_API_TARGET` (default http://localhost:8000). |
| `npm run test` | Vitest and Testing Library. |
| `npm run lint` | ESLint, and a check that the generated theme is current. |
| `npm run build` | Type check and production build into `dist/`. |
| `npm run theme` | Regenerate `src/theme/tokens.g.css` from `docs/brand/tokens.json`. Run it after the tokens change. |

## Deploy

The API's deploy workflow builds the portal into `services/api/portal` and uploads it with the API (`.github/workflows/api-deploy.yml`). The API serves that folder at `/portal/` and falls back to `index.html` for page paths (`services/api/app/webauth/portal.py`). Do not add `services/api/portal` to `.gitignore` or `.vercelignore`: the Vercel CLI would then leave it out of the upload.

## Local sign-in

Start the API (`uvicorn app.main:app` in `services/api`), then the dev server. Sign in with the admin user ID and password. The dev proxy removes the `Secure` flag from cookies so they work over plain http.

## Add a page

1. Add a row to `src/nav.ts` (path, label). It shows in the left navigation and gets a placeholder route.
2. Build the screen in `src/pages/<Name>.tsx`. Use the components from `src/components`.
3. In `src/App.tsx`, replace that area's `Placeholder` route with the new page (inside the `RequireAuth` and `Shell` routes).
4. Call the API with `api()` from `src/api/client.ts` inside TanStack Query hooks. It sends the cookie, adds the CSRF header on changes, and throws an `ApiError` with `code`, `message` and `fields`.
5. Add a test beside the page. Stub `fetch` as in `src/App.test.tsx`.

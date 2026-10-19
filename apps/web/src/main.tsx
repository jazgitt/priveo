// The style sheets load first, so ui.css fixes the order of the CSS layers
// before any page's own style sheet names one.
import "./theme/tokens.g.css";
import "./ui.css";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { AppRoutes } from "./App";
import { AnalyticsBridge } from "./analytics/AnalyticsBridge";
import { DEFAULT_HOST, initAnalytics } from "./analytics/analytics";
import { sharedReadOptions } from "./api/queryDefaults";
import { AuthProvider } from "./auth/AuthContext";
import { ToastProvider } from "./components";

initAnalytics({
  key: import.meta.env.VITE_POSTHOG_KEY ?? "",
  host: import.meta.env.VITE_POSTHOG_HOST ?? DEFAULT_HOST,
  replay: import.meta.env.VITE_POSTHOG_REPLAY === "true",
});

const queryClient = new QueryClient({
  defaultOptions: { queries: sharedReadOptions },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename={import.meta.env.BASE_URL}>
        <ToastProvider>
          <AuthProvider>
            <AnalyticsBridge />
            <AppRoutes />
          </AuthProvider>
        </ToastProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);

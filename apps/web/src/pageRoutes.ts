import type { RouteObject } from "react-router-dom";

import { routes as alerts } from "./pages/alerts";
import { routes as capacity } from "./pages/capacity";
import { routes as complaints } from "./pages/complaints";
import { routes as dashboard } from "./pages/dashboard";
import { routes as feedback } from "./pages/feedback";
import { routes as payments } from "./pages/payments";
import { routes as schedule } from "./pages/schedule";
import { routes as subscriptions } from "./pages/subscriptions";

/** Every built page. A nav path with no route here shows the placeholder. */
export const PAGE_ROUTES: RouteObject[] = [
  ...dashboard,
  ...alerts,
  ...payments,
  ...subscriptions,
  ...schedule,
  ...capacity,
  ...complaints,
  ...feedback,
];

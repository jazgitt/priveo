import type { RouteObject } from "react-router-dom";

import { routes as alerts } from "./pages/alerts";
import { routes as audit } from "./pages/audit";
import { routes as capacity } from "./pages/capacity";
import { routes as complaints } from "./pages/complaints";
import { routes as crew } from "./pages/crew";
import { routes as customers } from "./pages/customers";
import { routes as addons } from "./pages/addons";
import { routes as dashboard } from "./pages/dashboard";
import { routes as feedback } from "./pages/feedback";
import { routes as payments } from "./pages/payments";
import { routes as reference } from "./pages/reference";
import { routes as schedule } from "./pages/schedule";
import { routes as settings } from "./pages/settings";
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
  ...reference,
  ...settings,
  ...audit,
  ...crew,
  ...customers,
  ...addons,
];

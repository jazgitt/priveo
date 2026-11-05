import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import { ScheduledJobsPage } from "./ScheduledJobsPage";

export const routes: RouteObject[] = [
  { path: "/scheduled-jobs", element: createElement(ScheduledJobsPage) },
];

import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import { ManiPage } from "./ManiPage";
import { UsagePage } from "./UsagePage";

export const routes: RouteObject[] = [
  { path: "/mani", element: createElement(ManiPage) },
  { path: "/reports/agent", element: createElement(UsagePage) },
];

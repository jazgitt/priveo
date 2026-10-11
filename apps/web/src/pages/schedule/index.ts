import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import type { NavItem } from "../../nav";
import { SchedulePage } from "./SchedulePage";

export const routes: RouteObject[] = [{ path: "/schedule", element: createElement(SchedulePage) }];

export const nav: NavItem = {
  path: "/schedule",
  label: "Schedule",
  about: "Run the scheduler, review, change and freeze.",
};

import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import type { NavItem } from "../../nav";
import { DashboardPage } from "./DashboardPage";

export const routes: RouteObject[] = [
  { path: "/", element: createElement(DashboardPage) },
];

export const nav: NavItem = {
  path: "/",
  label: "Dashboard",
  about: "Today at a glance: visits, payments and issues.",
};

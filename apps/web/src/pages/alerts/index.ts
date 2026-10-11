import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import type { NavItem } from "../../nav";
import { AlertsPage } from "./AlertsPage";

export const routes: RouteObject[] = [
  { path: "/alerts", element: createElement(AlertsPage) },
];

export const nav: NavItem = {
  path: "/alerts",
  label: "Alerts",
  about: "Support and payment alerts in one list.",
};

import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import type { NavItem } from "../../nav";
import { SubscriptionsPage } from "./SubscriptionsPage";

export const routes: RouteObject[] = [
  { path: "/subscriptions", element: createElement(SubscriptionsPage) },
];

export const nav: NavItem = {
  path: "/subscriptions",
  label: "Subscriptions",
  about: "Plan, schedule settings, start and status.",
};

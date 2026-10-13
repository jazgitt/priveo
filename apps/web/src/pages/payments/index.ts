import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import type { NavItem } from "../../nav";
import { PaymentsPage } from "./PaymentsPage";

export const routes: RouteObject[] = [
  { path: "/payments", element: createElement(PaymentsPage) },
];

export const nav: NavItem = {
  path: "/payments",
  label: "Payments",
  about: "Due, over due and received payments.",
};

import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import type { NavItem } from "../../nav";
import { ComplaintDetailPage } from "./ComplaintDetailPage";
import { ComplaintsPage } from "./ComplaintsPage";

export const routes: RouteObject[] = [
  { path: "/complaints", element: createElement(ComplaintsPage) },
  { path: "/complaints/:id", element: createElement(ComplaintDetailPage) },
];

export const nav: NavItem = {
  path: "/complaints",
  label: "Complaints",
  about: "Complaints and visits that could not be done.",
};

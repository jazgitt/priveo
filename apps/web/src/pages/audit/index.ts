import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import type { NavItem } from "../../nav";
import { AuditPage } from "./AuditPage";

export const routes: RouteObject[] = [
  { path: "/audit", element: createElement(AuditPage) },
];

export const nav: NavItem = {
  path: "/audit",
  label: "Audit",
  about: "Who changed reference data and settings, and what changed.",
};

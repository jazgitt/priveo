import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import type { NavItem } from "../../nav";
import { AuditPage } from "./AuditPage";

export const routes: RouteObject[] = [
  { path: "/audit", element: createElement(AuditPage) },
];

export const nav: NavItem = {
  path: "/audit",
  label: "Audit trail",
  about: "Who changed this site's data, and what changed.",
};

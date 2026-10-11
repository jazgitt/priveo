import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import type { NavItem } from "../../nav";
import { ReferencePage } from "./ReferencePage";

export const routes: RouteObject[] = [
  { path: "/reference", element: createElement(ReferencePage) },
];

export const nav: NavItem = {
  path: "/reference",
  label: "Reference data",
  about: "Checklists, proof minimums and plans.",
};

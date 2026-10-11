import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import type { NavItem } from "../../nav";
import { CrewDetailPage } from "./CrewDetailPage";
import { CrewListPage } from "./CrewListPage";

export const routes: RouteObject[] = [
  { path: "/crew", element: createElement(CrewListPage) },
  { path: "/crew/:id", element: createElement(CrewDetailPage) },
];

export const nav: NavItem = {
  path: "/crew",
  label: "Crew",
  about: "Onboard crew, accounts and exceptions.",
};

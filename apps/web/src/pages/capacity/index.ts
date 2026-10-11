import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import type { NavItem } from "../../nav";
import { CapacityPage } from "./CapacityPage";

export const routes: RouteObject[] = [{ path: "/capacity", element: createElement(CapacityPage) }];

export const nav: NavItem = {
  path: "/capacity",
  label: "Capacity",
  about: "Working slots and capacity by society.",
};

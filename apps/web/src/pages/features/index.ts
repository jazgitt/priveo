import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import type { NavItem } from "../../nav";
import { FeaturesPage } from "./FeaturesPage";

export const routes: RouteObject[] = [
  { path: "/features", element: createElement(FeaturesPage) },
];

export const nav: NavItem = {
  path: "/features",
  label: "Features",
  about: "Switch app features on or off for customers and crew.",
};

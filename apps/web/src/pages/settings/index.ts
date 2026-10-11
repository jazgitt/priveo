import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import type { NavItem } from "../../nav";
import { SettingsPage } from "./SettingsPage";
import "./settings.css";

export const routes: RouteObject[] = [
  { path: "/settings", element: createElement(SettingsPage) },
];

export const nav: NavItem = {
  path: "/settings",
  label: "Settings",
  about: "Cutoff times, sessions and portal settings.",
};

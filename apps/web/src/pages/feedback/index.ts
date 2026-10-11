import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import type { NavItem } from "../../nav";
import { FeedbackPage } from "./FeedbackPage";

export const routes: RouteObject[] = [
  { path: "/feedback", element: createElement(FeedbackPage) },
];

export const nav: NavItem = {
  path: "/feedback",
  label: "Feedback",
  about: "Ratings, feedback and check-ins.",
};

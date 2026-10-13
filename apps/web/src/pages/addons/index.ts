import { createElement } from "react";
import type { RouteObject } from "react-router-dom";
import { AddonsPage } from "./AddonsPage";
export const routes: RouteObject[] = [{ path: "/addons", element: createElement(AddonsPage) }];

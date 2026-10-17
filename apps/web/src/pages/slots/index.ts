import { createElement } from "react";
import type { RouteObject } from "react-router-dom";

import { SlotsTab } from "../reference/SlotsTab";

export const routes: RouteObject[] = [{ path: "/slots", element: createElement(SlotsTab) }];

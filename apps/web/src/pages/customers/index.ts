import type { RouteObject } from "react-router-dom";
import { CustomerDetailPage, CustomersPage } from "./CustomersPage";
import { createElement } from "react";
export const routes: RouteObject[] = [
  { path: "/customers", element: createElement(CustomersPage) },
  { path: "/customers/:id", element: createElement(CustomerDetailPage) },
];

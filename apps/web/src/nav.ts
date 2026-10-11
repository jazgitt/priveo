// The admin areas, in the order of docs/reqs/admin-functional-requirements.md.
// To add a page: add a row here, then give its `path` a route in App.tsx
// (or leave it on the placeholder until the screen is built).
export interface NavItem {
  path: string;
  label: string;
  /** What the area covers, shown on the placeholder page. */
  about: string;
}

export const NAV: NavItem[] = [
  { path: "/", label: "Dashboard", about: "Today at a glance: visits, payments and issues." },
  { path: "/alerts", label: "Alerts", about: "Support and payment alerts in one list." },
  { path: "/customers", label: "Customers", about: "Onboard, find and update customers." },
  { path: "/subscriptions", label: "Subscriptions", about: "Plan, schedule settings, start and status." },
  { path: "/crew", label: "Crew", about: "Onboard crew, accounts and exceptions." },
  { path: "/schedule", label: "Schedule", about: "Run the scheduler, review, change and freeze." },
  { path: "/capacity", label: "Capacity", about: "Working slots and capacity by society." },
  { path: "/payments", label: "Payments", about: "Due, over due and received payments." },
  { path: "/addons", label: "Add-ons", about: "Deep Spa and other add-on requests." },
  { path: "/complaints", label: "Complaints", about: "Complaints and visits that could not be done." },
  { path: "/feedback", label: "Feedback", about: "Ratings, feedback and check-ins." },
  { path: "/operations", label: "Operations", about: "Skips by operations and daily jobs." },
  { path: "/reference", label: "Reference data", about: "Checklists, proof minimums and plans." },
  { path: "/settings", label: "Settings", about: "Cutoff times, sessions and portal settings." },
  { path: "/audit", label: "Audit", about: "Who changed reference data and settings, and what changed." },
];

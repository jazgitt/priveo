// The admin areas, in the order of docs/reqs/admin-functional-requirements.md.
// To add a page: add a row here, then give its `path` a route in App.tsx
// (or leave it on the placeholder until the screen is built).
export interface NavItem {
  path: string;
  label: string;
  /** What the area covers, shown on the placeholder page. */
  about: string;
  /** "site" pages follow the Site selector; "master" pages apply to every site. */
  group?: "site" | "master";
}

export const NAV: NavItem[] = [
  { path: "/", label: "Dashboard", about: "Today at a glance: visits, payments and issues." },
  { path: "/alerts", label: "Alerts", about: "Support and payment alerts in one list." },
  { group: "site", path: "/customers", label: "Customers", about: "Onboard, find and update customers." },
  { group: "site", path: "/subscriptions", label: "Subscriptions", about: "Plan, schedule settings, start and status." },
  { group: "site", path: "/crew", label: "Crew", about: "Onboard crew, accounts and exceptions." },
  { group: "site", path: "/schedule", label: "Schedule", about: "Run the scheduler, review, change and freeze." },
  { group: "site", path: "/slots", label: "Working slots", about: "Working slots of this site, by service." },
  { group: "site", path: "/capacity", label: "Capacity", about: "Working slots and capacity by society." },
  { group: "site", path: "/payments", label: "Payments", about: "Due, over due and received payments." },
  { group: "site", path: "/addons", label: "Add-ons", about: "Deep Spa and other add-on requests." },
  { group: "site", path: "/complaints", label: "Complaints", about: "Complaints and visits that could not be done." },
  { group: "site", path: "/feedback", label: "Feedback", about: "Ratings, feedback and check-ins." },
  { group: "site", path: "/operations", label: "Operations", about: "Skips by operations and daily jobs." },
  { group: "master", path: "/reference", label: "Master data", about: "Societies, base plans, services, checklists and the add-on catalogue." },
  { group: "master", path: "/settings", label: "Settings", about: "Cutoff times, sessions and portal settings." },
  { group: "master", path: "/audit", label: "Audit", about: "Who changed reference data and settings, and what changed." },
];

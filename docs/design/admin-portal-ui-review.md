# Admin portal: functional review and UI decisions

17-Oct-26. A review of how the admin uses the portal, so the rebuilt screens fit the work. It covers the
whole portal at the level of navigation and patterns, and the two pilot areas (Customers and Schedule) in
detail. Requirement IDs refer to `docs/reqs/admin-functional-requirements.md`. Nothing here changes a
requirement. Where a screen decision fills a gap, it is marked **UI decision** and can be reversed.

## 1. Who uses the portal and how

- One small operations team (the owner and an admin or two) working on a laptop or desktop, at 1280 to
  1920 px wide. Phones use the Flutter quick actions (ADM-ACC-07), so the portal is designed for desktop
  first and only has to stay usable on a tablet.
- The admin works on **one site at a time** (ADM-SITE-01). Every site page must say which site it shows.
- Most work is **find, check, change one thing**: a customer calls, the admin finds them, changes a
  cutoff time or skips a date, and moves on. Speed of finding and clarity of the current state matter
  more than dense dashboards.
- A few actions are **heavy or irreversible**: run the scheduler, freeze or unfreeze, make a subscription
  Inactive, correct an email (clears the password and signs the customer out), clear a password, sign out
  sessions. These need a confirmation and a visible result.
- Customers are **not notified** of admin changes (ADM-CUS-14). The only feedback the admin gets that a
  change took effect is the portal itself, so every save must say clearly that it worked or why it did
  not.

## 2. Portal-wide decisions

| Topic | Decision |
|---|---|
| Component library | shadcn/ui (Radix primitives, Tailwind CSS), themed from `docs/brand/tokens.json`. No more hand-built dropdowns, dialogs or tooltips. |
| Type | Manrope for all interface text. Cormorant Garamond only for the "Priveo" wordmark: a display serif is hard to read at table and heading sizes. |
| Density | Admin density, not phone density: 36 px controls (the 48 px touch size stays in the app), 14 px body text in tables, 8 px spacing grid. |
| Page frame | Every page has the same header: title, one line on what it is for, the site it shows, and the page's main action on the right. |
| Data lists | One table component: fixed column widths, long text cut with an ellipsis and shown in full on hover, row hover, a whole-row link where a row opens something, a loading skeleton, an empty state that says what to do next, and paging. |
| Record details | Label and value grids, never sentences joined with "·". A value that is missing shows "-". |
| Editing | A record is shown read-only first. Editing opens a side sheet or a dialog with its own Save and Cancel, so a half-typed form never mixes with what is saved. |
| Saving | Every change shows "Saving…", then "Saved" or the reason it failed, from one shared hook. The control that started it shows a spinner and is disabled while it runs. |
| Confirmation | Anything that deletes, signs out, clears, freezes, unfreezes, ends or deactivates asks first, in a dialog that names the record and says what will happen. |
| Long actions | A run that takes more than a moment (the scheduler) shows a progress panel with the elapsed time and what is happening. The admin can leave the page; the result arrives as a notification with a link to it. |
| Status | Status chips use one colour set everywhere: Active/Received green, Activating/Due amber, Inactive/Over due red, Frozen blue, Draft grey. |
| Dates | `dd-Mon-yy` everywhere (for example 07-Nov-26), with the weekday where the day matters (schedules). Prices as "₹999", GST included. |
| Loading speed | Each page's code loads when it is first opened. A save updates only what changed. Fonts are compressed (woff2). |

## 3. Customers (ADM-CUS-01 to ADM-CUS-21, ADM-SUB-01 to ADM-SUB-05)

### What the admin does here

1. Finds a customer by name, mobile, registration or society (ADM-CUS-08). Usually by registration or
   mobile, because that is what a caller gives.
2. Checks their state: onboarding progress (ADM-CUS-17), each vehicle's subscription status, plan and
   schedule settings, and payments.
3. Makes one change: schedule settings, skip or pause on the customer's behalf (ADM-CUS-09), plan at next
   renewal (ADM-CUS-15), subscription status (ADM-SUB-01, -02, -04), car or parking details, notification
   switches (ADM-CUS-12), email correction or password clear (ADM-CUS-19, -20), sessions (ADM-CUS-21).
4. Less often: creates a customer with the first vehicle (ADM-CUS-01), or adds a vehicle (ADM-CUS-05).

### Problems found in the current screens

| # | Problem | Kind |
|---|---|---|
| C1 | The list shows only name, email and mobile. The admin cannot see the vehicles, the society or whether anything needs attention without opening each customer. | Layout |
| C2 | "·" and "₹" show as "Â·" and "â‚¹" in several places (a file encoding error). | Bug |
| C3 | The first service date field and the skip date field share one value. Typing a skip date also fills the first service date sent with a status change, and the other way round. | Functional bug |
| C4 | Subscription status is a free dropdown of all three statuses. The backend only allows Activating to Active, any to Inactive, and Inactive to Activating, so most choices fail. Inactive needs a reason (ADM-SUB-02) but the reason is optional. | Functional |
| C5 | Correct email, Clear password, Sign out session and Sign out all sessions run at once with no confirmation, though each signs the customer out. | Missing confirmation |
| C6 | Interior care day is offered for every plan, though it applies only when the plan includes interior care. | Functional |
| C7 | Every edit form is open on the page at once, inside collapsible sections. Saved values and typed-but-unsaved values look the same. | Layout |
| C8 | Payments are listed as sentences; current skips and pauses appear only inside the editing section. | Layout |

### Layout decisions

- **List**: search box with the page action "Create customer". Columns: Customer (name, with flat below),
  Contact (mobile, email), Vehicles (registration and subscription status chip for each), Onboarding
  (verified / password / review as a short status). The whole row opens the customer. This needs the list
  endpoint to return each customer's flat, vehicles and onboarding flags (an additive change to
  `GET /v1/admin/customers`).
- **Detail**: header with the name, contact and onboarding status, and the account actions in a menu
  (Correct email, Clear password, Sign out all sessions), each with a confirmation.
  - Main column: one panel per vehicle. The panel shows the vehicle photo, registration, make and model,
    parking and society; the subscription (status, plan, price, cutoff, interior day, first service date,
    plan change pending); upcoming skips and pauses with Un-skip and End pause; and recent payments as a
    small table.
  - Each panel has buttons that open a focused dialog: **Edit car and parking**, **Schedule settings**
    (cutoff, interior day only when the plan includes it, plan at next renewal), **Skip a date**,
    **Pause**, and the subscription action that is valid now: **Activate** (Activating, asks for the first
    service date), **Make inactive** (asks for a reason), **Reactivate** (Inactive). **UI decision**:
    the status choice is reduced to the valid next step, matching the backend's rules.
  - Side column: customer details (edit in a dialog), notification switches (each switch saves at once
    with a toast), signed-in sessions with Sign out (confirmed).
- **Create customer / Add vehicle**: kept as a step-by-step dialog (it mirrors the customer's own
  onboarding, ADM-CUS-01), with a visible step bar, fields in a two-column grid, a photo preview, and a
  review step laid out as label and value pairs.

## 4. Schedule (ADM-SCH-01 to ADM-SCH-33)

### What the admin does here

1. Before the period: runs the scheduler for the site and period (ADM-SCH-01, -09). This takes several
   seconds.
2. Reviews the draft on the Board, day by day, per crew member (ADM-SCH-12, -33), sees what is
   unscheduled and why (ADM-SCH-08), and fixes by hand: move, swap, take off, place (ADM-SCH-13).
3. Optionally runs again or applies suggested improvements (ADM-SCH-14, -15).
4. Freezes before 8 PM the day before (ADM-SCH-16, -25).
5. After the freeze: handles cutoff change requests (ADM-SCH-22, -23) and the Needs scheduling list
   (ADM-SCH-28), unfreezing with the code when work must be added or moved (ADM-SCH-17, -18).

### Problems found in the current screens

| # | Problem | Kind |
|---|---|---|
| S1 | Run Scheduler gives no feedback for several seconds except a disabled button. Leaving the page loses the result. | Feedback |
| S2 | Changing the Period dropdown on the Run tab silently saves it as the portal-wide preference (ADM-PRF-01) for every later run. | Functional |
| S3 | The schedule's status, period and freeze deadline are only on the Board tab. From the other tabs the admin cannot see whether the schedule is a draft or frozen. | Layout |
| S4 | Cutoff requests and add-ons awaiting a period are printed as sentences with buttons inline; Apply and Reject run at once without confirmation. | Layout, confirmation |
| S5 | Draft improvements: the job pickers are long unlabelled lists; the suggestion checkboxes are loose labels. | Layout |
| S6 | Take off crew member runs without confirmation. | Confirmation |
| S7 | ADM-SCH-12 asks for review by day, by crew member and by customer or society. The Board gives the day view with crew rows; there is no list by customer. | Gap (noted, not built in this pilot) |

### Layout decisions

- **Schedule header** above the tabs, on every tab: site, period (start to end), status chip, freeze
  deadline or frozen time, and the actions Run again, Freeze or Unfreeze. The admin always knows what
  state the schedule is in.
- **Run tab**: period and start date side by side with the computed range shown ("Sun 18-Oct-26 to
  Sat 24-Oct-26"). The Period choice applies to this run only; a separate "Make this the default period"
  link saves the preference. **UI decision** (S2).
- **Running**: a progress panel (spinner, elapsed time, "Placing jobs for DLF Meadows…") that stays in the
  page header area even if the admin moves to another page. When it ends, a notification gives placed,
  unscheduled and late counts and opens the Board. The run itself still takes as long as before; making
  it a true server background job needs a hosting decision (section 5).
- **Board tab**: day picker as a strip of day cards (weekday, date, booked/demand minutes, unscheduled
  count, over-capacity in red); the Gantt chart below; unscheduled jobs of the day as a table below that.
  Job dialog laid out as details plus a move form; Take off is confirmed.
- **Needs scheduling, Cutoff requests, Draft improvements**: tables with one row per item and the row's
  actions at the right end. Apply, Reject, Swap and Apply selected each confirm what they will do.

## 5. Not in this pilot

- The other pages keep their current screens, with the refreshed base styles, until they are rebuilt in
  the next batches on the same components.
- A true background job for the scheduler (the API answers at once and the work runs on a worker) needs
  a job table and a worker process. On the current Vercel dev host a function cannot keep running after
  it answers. This fits the planned AWS ECS hosting; decide when hosting moves.
- S7 (schedule list by customer) is a gap against ADM-SCH-12, to be scheduled.

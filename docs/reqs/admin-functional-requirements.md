# Priveo Car Concierge: Admin Functional Requirements

**Status:** Draft v0.58 (crew working hours mandatory, owner decision of 7 Nov 2026; scheduling rules v1.2 applied, owner decisions of 5 Nov 2026: weekly off, 30-minute jobs, Interior entitlement, service week, cutoff policy, break, zones, deferral; rows ADM-SVS-01, ADM-SVS-05, ADM-SVS-09, ADM-SVS-10, ADM-SCH-04, ADM-SCH-05, ADM-SCH-07, ADM-SCH-08, ADM-SCH-09, ADM-SCH-26, ADM-SCH-33, ADM-SCH-41, ADM-CNC-03, ADM-CNC-06, ADM-CNC-10, ADM-CAP-01, ADM-CAP-08, ADM-PRF-01, ADM-SUB-10, ADM-CRW-04, ADM-CRW-25, ADM-REF-08, ADM-SET-07 and business rules 4 to 6 changed; the new behaviour is described in `scheduler-requirements.md` and is not yet built or live, 6 Nov 2026), v0.56 (ADM-SCH-33: pinned Unscheduled column, foldable lanes, hide crew who are off, drag to pan, 5 Nov 2026), v0.55 (ADM-SCH-33: Focus view and the Board in its own browser tab, 5 Nov 2026), v0.54 (ADM-SCH-33: a Table view, one search over customer, crew, model and parking, Late and By hand chips and a crew picker, 5 Nov 2026), v0.53 (ADM-SCH-33, ADM-SCH-34: cards coloured by kind of work, card detail choice, drag feedback, instant moves with Undo, 5 Nov 2026), v0.52 (ADM-SCH-32, ADM-SCH-33, ADM-SCH-35: the Schedule page gives the Board the whole window, Run is a button, the day strip folds away, 5 Nov 2026), v0.51 (ADM-SET-09: the Actor ID filter is replaced by a general search of 3 or more characters, run by a Search button or Enter; the Site column is removed, 5 Nov 2026), v0.50 (last name optional and mobile entry limited to 10 digits, 5 Nov 2026: ADM-CUS-01, ADM-CUS-24, ADM-CRW-02), v0.49 (ADM-FLAG-01: the page is named Feature Plugs and is split into tabs for Customers, Crew and Both apps, 5 Nov 2026), v0.48 (scheduled jobs: ADM-OPS-05 to ADM-OPS-09 new, ADM-CMP-08 and ADM-SET-05 changed, 5 Nov 2026), v0.47 (Audit trail: changes that belong to no site are marked "All sites" and shown in every site's trail, owner decision of 5 Nov 2026; ADM-SET-09 and ADM-SITE-01 changed; Audit trail: renamed from Audit, moved under "This site", 50 events a page; ADM-SITE-01, ADM-SET-06, ADM-SET-07, ADM-REF-08, ADM-REF-10 changed, new ADM-SET-09, 5 Nov 2026), v0.46 (ADM-CAP-08: a weekday the site has no working slot for a service has no demand for it, 4 Nov 2026), v0.45 (ADM-CUS-35: the vehicle panel in tabs, Vehicle details, Service history and Payments, 4 Nov 2026), v0.44 (payment status rework: ADM-PAY-01, 02, 03, 06, 07, 12, new ADM-PAY-14 and ADM-PAY-15, pause no longer moves the cycle, 4 Nov 2026), v0.43 (ADM-REF-09 and ADM-REF-10: the zone is internal and never shown to the customer; ADM-CUS-27 the parking number of a change is free text up to 60 characters and the basement may be empty with a zone, 3 Nov 2026), v0.42 (customers sign in with the mobile number and MPIN: ADM-CUS-01 to ADM-CUS-04, ADM-CUS-17 to ADM-CUS-21, ADM-CUS-24 and ADM-CUS-30 changed; ADM-CUS-33 first MPIN, ADM-CUS-34 mobile number change; owner decision of 3 Nov 2026), v0.41 (ADM-REF-10 zone and parking slot always shown together; zone changes audited, 3 Nov 2026), v0.40 (ADM-CUS-01 parking number is free text and the basement is optional with a zone, 3 Nov 2026), v0.39 (ADM-CUS-31 alternate names shown and edited; ADM-CUS-32 search by alternate names, parking and zone; ADM-CUS-01 email optional, 3 Nov 2026), v0.38 (ADM-SUB-11 set up a subscription for a vehicle that has none; ADM-REF-08, ADM-REF-09 zones; ADM-CUS-30 customer without email; ADM-SUB-10 Custom interior day, 3 Nov 2026), v0.37 (ADM-PAY-06: an add-on payment becomes Over due immediately after its service completes, in line with ADM-PAY-13, 31 Oct 2026), v0.36 (ADM-SET-04: the admin edits the invoice seller values; ADM-SET-08 lets a plan be linked to a vehicle category, stored and shown only; ADM-CNC-10 reschedules for the next day only; customer notified of a Partially Completed visit, CAL-11; rows confirmed by the owner on 25 Oct 2026 are marked Owner; vehicle service history by state ADM-CUS-29 detailed; schedule patterns ADM-SCH-41 built as Weekly and Cycle; plan change from a chosen date ADM-SUB-08 detailed; parking changes ADM-CUS-27 detailed; skip no longer extends the plan, mandatory remark, crew queue, Partially Completed, schedule patterns and other items from the owner review of 23 Oct 2026; see owner-decisions-2026-10-23.md), v0.26 (feature flags, 23 Oct 2026), v0.25 (portal usage-data notice, 19 Oct 2026; summary tiles that filter, list and tile views, Capacity Utilisation, Site Setup, Settings tabs and a manual Audit refresh, 18 Oct 2026; customer page in tabs with summary numbers and status tabs, vehicle tiles, vehicle deactivation, address lines; RC document and mandatory vehicle photo removed for the admin, 18 Oct 2026; wrong passwords block admin and crew logins for a growing time instead of locking them, 18 Oct 2026; Schedule page led by one chosen day; Board as Cards with a view-only Timeline, 18 Oct 2026; skipped and paused jobs on their own tab; Board shows all days and several chosen days; job status colours and counts on the Board; site selector; multiple working slots a day; crew page tabs and edit icon; Trainees move with their Member; crew society moves from a date; plan and add-on IDs; complaint 4-hour target is internal only; welcome email not resendable, 16 Oct 2026): owner decisions of 9 Oct 2026; crew-driven additions; email sign-in for customers; Deep Spa is an add-on for subscribers and a standalone service for others (owner decision of 10 Oct 2026); admin web portal in MVP with a limited set of mobile quick actions; consistency pass
**Scope:** Phase 1, Part 2 (Admin), MVP. Customer features are in `customer-app-functional-requirements.md`. Crew features (Part 3) are in `crew-functional-requirements.md`.
**Platforms:** A React web portal with every admin function, and a limited set of simple admin actions in the Flutter mobile app (section 1a). The web portal and the mobile app use the same backend.
**Language:** English only

## How this document was built

Sources:

- The admin feature list you gave on 9 Oct 2026 (items a to l) and your answers to the questions in section 13.
- The customer requirements file, for the rules the admin features must respect or that already depend on an admin feature.

Rules followed:

- Each requirement has an ID. Admin IDs start with `ADM-`.
- **Status** column:
  - **Owner**: you stated it.
  - **Derived**: not stated, but needed to make a stated item work, or taken from the customer requirements. Please check these.
  - **Open**: depends on a question in section 13.
- Everything in this file is **MVP** unless section 14 says otherwise.
- Crew role privileges are in `crew-functional-requirements.md` (section 3a for Managers, section 3 for Members and Trainees). Where a Manager can do something an admin can also do, the admin file notes it.

## Contents

1. Access and roles
2. Customers
3. Crew
4. Services and working slots
5. Capacity
6. Payments
7. Scheduling
8. Complaints, feedback and ratings (includes visits the crew could not complete, 8.2a)
9. Reference data and settings (includes service checklists and proof minimums, 9.1, and add-ons, 9.2)
10. Business rules
11. Data entities implied by the requirements
12. Customer requirements and the admin features that cover them
13. Open questions
14. Deferred to V2 and out of scope

---

Owner decisions of 13 Oct 2026 supersede earlier fixed-policy/undecided wording; see [the decision record](owner-decisions-2026-10-13.md).

## 1. Access and roles

| ID | Requirement | Status |
|---|---|---|
| ADM-ACC-01 | All admin functions are available on a web portal, in MVP. A limited set of simple admin actions is also available in the mobile app (ADM-ACC-07). | Owner (item l, revised) |
| ADM-ACC-02 | Admin screens are available only to users with the Admin role. | Derived |
| ADM-ACC-03 | Crew members have one of three roles: **Manager**, **Member**, **Trainee**. The Admin role is separate from these. | Owner (item c) |
| ADM-ACC-04 | Customers and crew use the mobile app. Admins use the web portal and the mobile quick actions. Each person has their own login, and the role set for it in the backend decides what they can see and do. | Owner |
| ADM-ACC-05 | Admin accounts are loaded into the database by a seed when the application is set up. There is no admin sign-up or admin creation in the app in MVP. An admin signs in on the same login screen with a user ID and a password (CRW-ACC-02 in the crew file). The first admin has the user ID `priveopapa`. Its password is supplied through the environment configuration (`.env`) at setup, and is not stored in the repository or the documents. | Owner |

### 1a. Web portal and mobile quick actions

| ID | Requirement | Status |
|---|---|---|
| ADM-ACC-06 | An admin signs in to the web portal with the same user ID and password as in the app (ADM-ACC-05). The wrong-password block applies (CRW-ACC-07 in the crew file): 15 minutes, then 1 hour, then 24 hours. If the admin must get in sooner, the seed is run again (ADM-ACC-05). | Owner and Derived |
| ADM-ACC-07 | The mobile app gives the admin a limited set of **quick actions**: (a) phone push alerts (ADM-ACC-09); (b) confirm or reject a payment, that is, set its status (ADM-PAY-02); (c) see the Needs scheduling list and the day's schedule, read-only; (d) mark a visit skipped by operations, and choose the outcome of a Missed job (ADM-OPS-01, ADM-CNC-03); (e) skip, un-skip, pause and end a pause for a customer's vehicle, on behalf of the customer (ADM-CUS-09); (f) other simple actions that are not complex transactions: search and view customers, view and update complaints (status and notes), view feedback, ratings and check-in results, view capacity, view the crew list and add crew exceptions, and view add-on requests. | Owner |
| ADM-ACC-08 | Everything else is **web portal only**: creating and editing customers, vehicles, subscriptions and schedule settings (the plan, service cutoff time and interior care day; skip, un-skip and pause are also on mobile, ADM-ACC-07); creating add-on requests; onboarding crew, roles, Trainee pairing, working hours, deactivation, password resets and crew and customer session management (ADM-CRW-21, ADM-CUS-21); services and working slots; running, reviewing, editing, freezing and unfreezing the scheduler; preferences; reference data and settings (societies, vehicle catalogue, plans, add-ons, checklists, reason lists, feedback and check-in categories, payment, support and invoice settings); GST invoice generation; and audit views. | Owner |
| ADM-ACC-09 | Admin alerts (ADM-SCH-24) reach the admin in three ways: a phone push in the mobile app, a notification bell with an unread count in the web portal, and an email for each alert. The admin can switch the emails off. The bell and the phone push cannot be switched off. | Owner |
| ADM-ACC-10 | The web portal and the mobile app use the same backend and the same rules. A change made in one shows in the other at once, and the last change wins, as in ADM-CUS-10. | Derived |
| ADM-ACC-11 | The list of mobile quick actions is expected to shrink. Actions that turn out to be complex for a phone are removed from the mobile app and stay on the web portal. | Owner |
| ADM-ACC-12 | The web portal keeps the admin signed in with an HttpOnly, secure cookie, not with tokens in browser storage, and every change request carries CSRF protection. A web session ends after 60 minutes of inactivity, and the admin signs in again. | Owner |
| ADM-ACC-13 | In the mobile app an admin stays signed in until they log out, their password is changed, or they have not used the app for 24 hours, and then they sign in again. The 60-minute inactivity time-out applies only to the web portal (ADM-ACC-12). Because the admin password is set at seed time, a lost admin phone is also handled by "Sign out of all devices" (ADM-ACC-14). | Owner |
| ADM-ACC-14 | The admin has a **Sign out of all devices** action, on the web portal and in the mobile app. It ends every session of the admin's own login, on the web and on phones, at once, including the one in use. The admin then signs in again where needed. The action is recorded with the time. | Owner |
| ADM-ACC-15 | When usage analytics is set up in the build, the web sign-in page tells the admin that Priveo records how the portal is used, including what is on screen, to improve it. The data goes to PostHog in the EU region. It identifies the admin by login ID and role only, never by name. A recording shows the screens as they are, with nothing masked except password fields (owner decision, 19 Oct 2026; what to mask is still to be decided), and recording is off unless switched on in the build. There is no opt-out switch yet. | Derived (EU region: Owner) |
| ADM-ACC-16 | The admin has a daily dashboard that shows, for a chosen day, the number of services Completed, Pending, Missed and Partially Completed. The admin can filter it by crew member and by vehicle. | Owner (confirmed 25 Oct 2026) |

---

## 2. Customers

### 2.1 Onboard a customer manually (item a)

| ID | Requirement | Status |
|---|---|---|
| ADM-CUS-01 | The admin can create a customer on the customer's behalf. The form follows the customer's own onboarding: first name (required), last name (optional, letters only when given), mobile number (required, at most 10 digits can be typed and exactly 10 are needed, the customer's sign-in ID); email (optional, a contact, ADM-CUS-30); society (starts as the site the admin is working on; a society must already exist, so a customer cannot be created without one); vehicle (make, model, variant, registration number, optional photo); parking (basement, which may be left empty when a zone is chosen; number, free text up to 60 characters); plan; service cutoff time; interior care day (only when the plan includes it). | Owner (last name optional, mobile entry: 5 Nov 2026) |
| ADM-CUS-02 | The same validation as customer onboarding applies: 10-digit mobile number, a valid email address when one is given, registration number format, required fields. | Derived |
| ADM-CUS-03 | A mobile number can belong to only one customer. A duplicate is refused when the admin creates or edits a customer, with the message "This mobile number already belongs to another customer". An email can also belong to only one customer. If it already exists, the app opens that customer instead of creating a duplicate. | Derived and Owner |
| ADM-CUS-04 | After the admin creates a customer who has an email, a welcome email is sent. It says the account is ready and asks them to open the app and sign in with their mobile number and the first MPIN, which is the last 6 digits of that number (ADM-CUS-33). It contains no code. The customer then chooses their own MPIN and reviews the details the admin entered (AUTH-19, ONB-25 in the customer file). No SMS is sent. A customer with no email gets no message, and the admin tells them the first MPIN outside the app. | Owner |
| ADM-CUS-05 | The admin can add further vehicles to an existing customer. Each vehicle has its own subscription. | Derived |
| ADM-CUS-06 | The admin does not choose a payment status when onboarding. The first cycle's payment record is created with the subscription and its status is worked out by the rules in PAY-14 from the cycle dates and today's date, the same as for every other cycle. A customer loaded by script gets the same: after the load the daily job (ADM-PAY-14) creates the record and the same rules give the status. If the customer has already paid, the admin records the payment (ADM-PAY-04). | Owner (4 Nov 2026) (replaces setting the first payment's status) |
| ADM-CUS-07 | The vehicle photo is optional when the admin adds a vehicle. The admin can upload it then or later, and the customer can replace it in their own app. A customer adding a vehicle in their own app still has to give a photo. | Owner (admin); Derived (customer rule unchanged) |

### 2.2 Find and view customers

| ID | Requirement | Status |
|---|---|---|
| ADM-CUS-08 | The admin can search the customer list by name, mobile number, registration number or society, and open a customer to see their vehicles, subscriptions, schedule settings and payment statuses. The list is paged and says how many customers there are and which page the admin is on. | Derived |
| ADM-CUS-17 | In the customer view the admin sees the customer's **app onboarding**: whether they have chosen their own MPIN (instead of the first one), verified their email and confirmed the onboarding review. | Derived |
| ADM-CUS-18 | Removed (owner, 16 Oct 2026): the admin cannot resend the welcome email. The welcome email is sent once, when the customer is created (ADM-CUS-04) or the email is corrected (ADM-CUS-19). | Owner |
| ADM-CUS-19 | The admin can update a customer's email. The email is a contact only: the customer's sign-in and sessions do not change. The email shows as not verified, and a new welcome email is sent. The change is audited (ADM-CUS-16). | Owner |
| ADM-CUS-20 | The admin can reset a customer's MPIN. It goes back to the first MPIN (the last 6 digits of the mobile number, ADM-CUS-33), all the customer's sessions end, and the customer must choose a new MPIN at the next sign-in (AUTH-19). This also gives a sign-in to a customer who has none. The change is audited (ADM-CUS-16). This is how a customer with no email recovers a forgotten MPIN (AUTH-16). | Owner and Derived |
| ADM-CUS-21 | The admin can manage a customer's signed-in sessions. The admin sees each active session with its device name, platform, app version and last-active time, and can sign out one session or all of the customer's sessions. The customer is signed out at once and sees the sign-in screen the next time the app contacts the server. Each sign-out is recorded with the admin and the time (ADM-CUS-16). Resetting a customer's MPIN or changing their mobile number (ADM-CUS-20, ADM-CUS-34) also ends all their sessions. | Owner |
| ADM-CUS-22 | At the top of the customer list the admin sees the total number of customers, how many have a subscription, how many have only add-ons (no subscription) and how many are Active, Activating and Inactive. The numbers follow the search and the site. Choosing a tile filters the list to what it counts, and choosing it again clears the filter. | Owner |
| ADM-CUS-23 | The customer list has tabs for All, Active, Activating, Inactive and No subscription, each with its count. A customer's status is that of their best subscription (Active, then Activating, then Inactive); a customer with none is No subscription. | Owner (tabs); Derived (how a status is chosen) |
| ADM-CUS-24 | A customer opens in tabs. **Account details** holds the fixed details (first name, last name (optional), email, mobile (at most 10 digits can be typed), flat, society, address lines 1 and 2, app onboarding), notifications, signed-in sessions and the account actions (update email, reset MPIN, sign out all sessions), and each part can be edited there. **Vehicles** holds the vehicles. Address lines and society are optional; empty address lines start from what was entered when the society was created, and the society starts as the site the admin is working on. | Owner (last name optional: 5 Nov 2026) |
| ADM-CUS-25 | In the Vehicles tab the admin sees one vehicle at a time. With more than one vehicle, small tiles with the vehicle's photo and registration number let the admin pick one. The admin can add, edit and **deactivate** a vehicle, and reactivate it. A deactivated vehicle gets no new visits, is hidden from the customer's app and the schedule, and keeps its history. A vehicle whose subscription is Active or Activating cannot be deactivated until the subscription is made Inactive. | Owner (deactivate); Derived (the subscription rule) |
| ADM-CUS-26 | The customer list and the subscription list (ADM-SUB-07) can be shown as a table or as a grid of tiles, one for each customer or subscription. The grid fits as many columns as the screen width allows. The choice applies to every tab of that page and is remembered in the browser. | Owner |
| ADM-CUS-27 | The admin can change a vehicle's parking location temporarily (with start and end dates) or permanently (from a date). The crew sees the current parking slot on the job card (CRW-SCH-17). Earlier locations are kept in history. The vehicle's own slot is not changed. A change can be cancelled and stays in the history. When changes overlap on a day, the one made last applies. The admin schedule and the crew job card show the slot valid on the job's date. The parking number is free text up to 60 characters, and the basement may be left empty when the vehicle has a zone, as for the vehicle's own parking (ADM-CUS-01). | Owner (confirmed 25 Oct 2026; free text 3 Nov 2026) |
| ADM-CUS-28 | In the Vehicles tab (ADM-CUS-25) the admin sees a read-only view of the crew who serve the vehicle, taken from its scheduled jobs. | Owner |
| ADM-CUS-29 | A vehicle's service history shows each service with one of these states: Scheduled, Completed, Partially Completed, Not Completed, Rescheduled, Cancelled (HIST-04 in the customer file). The admin can filter the history by state and sees how many services are in each state. A rescheduled service shows its original and revised dates. A visit with some jobs done and some missed is Partially Completed and stays in the history after a reschedule. A visit whose jobs were all skipped shows as Cancelled. The history does not show a customer name or mobile number. | Owner (confirmed 25 Oct 2026) |

### 2.3 Update plan and schedule settings (item g)

| ID | Requirement | Status |
|---|---|---|
| ADM-CUS-09 | The admin can change the plan of a vehicle's subscription (ADM-SET-01), and the schedule settings the customer can also change themselves: service cutoff time, interior care day, skip and un-skip a date, pause, and end a pause early. | Owner (item g) |
| ADM-CUS-10 | The customer can make the same changes in their own app. Whichever happens last is the current state, and the change shows in both. | Owner |
| ADM-CUS-11 | The 9 PM deadline (SCHED-01, SCHED-02 in the customer file) applies to customers only. The admin is not bound by it, so the admin can make a change after 9 PM, for example when a customer calls the helpline. Onboarding is not affected by the deadline either. | Owner |
| ADM-CUS-14 | When the admin changes a customer's plan or schedule settings, the customer is not notified. | Owner |
| ADM-CUS-15 | When the admin changes a subscription's plan, the new plan and its price start on the next renewal date. The current 30 days continue on the old plan and price. The customer is not notified (ADM-CUS-14). Changing plan by the customer is V2. | Owner |
| ADM-CUS-16 | Every admin change to a customer, vehicle, subscription, schedule setting, car detail or notification switch is recorded with the admin and the time (audit entry), because the customer is not notified of it. | Derived |

### 2.4 Customer notification settings (item i)

| ID | Requirement | Status |
|---|---|---|
| ADM-CUS-12 | The admin can see and switch on or off each of a customer's notification events: service completed, service skipped, complaint update, renewal reminder, monthly check-in. These are the same switches as the customer's Settings. | Owner (item i) |
| ADM-CUS-13 | The most recent change wins, whether it came from the customer or the admin. | Derived |
| ADM-CUS-30 | A customer can exist **without an email**, for example when loaded from a sheet. They sign in with the mobile number and the first MPIN like any customer (ADM-CUS-33), receive no email, and the portal shows "No email". Forgot MPIN by emailed code is not available to them, so the admin resets the MPIN (ADM-CUS-20). When the admin adds an email (the same action as ADM-CUS-19), the customer gets a welcome email. A customer can also hold **alternate names** (another person known on the account), shown, edited and searched as in ADM-CUS-31 and ADM-CUS-32. | Owner |
| ADM-CUS-31 | A customer's **alternate names** (other names the customer is known by) show on the customer's page and the admin can change them in Edit details. Emptying the field clears them. A change to the alternate names is **not** written to the audit log. | Owner (3 Nov 2026) |
| ADM-CUS-32 | The customer search (ADM-CUS-08) also matches a customer's alternate names, a vehicle's parking number and a vehicle's zone name. | Owner (3 Nov 2026) |
| ADM-CUS-33 | Every customer gets a sign-in when they are created, whether by the admin, by the customer workbook import or by the sheet load. The login ID is the mobile number and the first MPIN is its last 6 digits. The customer must change it at the first sign-in (AUTH-19). Customers who existed before 3 Nov 2026 were moved to this sign-in in one run of a script (see the owner decision note); their old passwords stopped working. | Owner |
| ADM-CUS-34 | When the admin changes a customer's mobile number, the sign-in moves to the new number and the customer's sessions end. A customer who still has the first MPIN gets the last 6 digits of the new number as the first MPIN. A customer who has chosen their own MPIN keeps it. | Derived |
| ADM-CUS-35 | In the Vehicles tab (ADM-CUS-25) the open vehicle's panel shows its content in three tabs, one at a time: **Vehicle details** (the car, subscription, skips and pauses, crew, parking and zone), **Service history** (ADM-CUS-29, with the count of services) and **Payments** (with the count of payments). Vehicle details is open first. Each tab can be reached with the keyboard (arrow keys) and its header is at least 40 px high for touch. | Owner (tabbed vehicle view); Derived (which tabs, and their names) |

---

### 2.5 Subscription start and status

| ID | Requirement | Status |
|---|---|---|
| ADM-SUB-01 | A new subscription starts as **Activating**. The admin chooses when it becomes **Active** and sets its first service date, whatever the payment status. The billing cycle starts on that first service date (rule 26 in the customer file). Visits are scheduled only for Active subscriptions. | Owner |
| ADM-SUB-02 | The admin can set a vehicle's subscription to **Inactive**, with a reason. Its future visits are removed from schedules (without the code, ADM-SCH-29), and the vehicle no longer counts in capacity demand (ADM-CAP-03) or in "cars serviced" (ADM-REF-02). The customer sees Inactive. | Owner and Derived |
| ADM-SUB-03 | The backend sets a subscription to Inactive automatically when its plan payment has been **Over due for 7 days**. An Over due add-on payment does not do this. The admin is alerted (ADM-SCH-24). The admin can override it. | Owner |
| ADM-SUB-04 | The admin can reactivate an Inactive subscription: it returns to Activating, and the admin then sets the first service date and activates it as in ADM-SUB-01. A new billing cycle and a new Due payment start from that date. Renewal by the customer is V2. | Derived |
| ADM-SUB-05 | Every change of subscription status is recorded with the admin, or the backend, and the time. | Derived |
| ADM-SUB-06 | At the top of the Subscriptions page the admin sees summary tiles: total subscriptions, how many are Active, Activating, Paused and Inactive, how many have a payment due (the latest plan payment is Due or Over due), and how many there are on each plan. Choosing a tile filters the list to what it counts. Tabs for All, Active, Activating, Paused and Inactive sit above the list, with their counts. | Owner |
| ADM-SUB-07 | The Subscriptions page can be shown as a table or as tiles, as in ADM-CUS-26. | Owner |
| ADM-SUB-08 | The admin can change a subscription's plan from a date the admin chooses. The plan history is kept with each plan and its effective date. A change made without a date still starts on the next renewal date (ADM-CUS-15). The date is today or later. Visits follow the new plan from that date. The next payment that is created uses the new price, and a payment that already exists keeps its price (ADM-SUB-09). When the date is before the renewal, the admin decides for that customer, at that time, what to charge for the days in between: no charge (the default), the prorated price difference, or an amount the admin enters. A charge is a separate one-off payment due on the start date. It never makes the subscription Inactive. Cancelling the change voids a charge that is not yet received. A new change replaces one that has not started, and the admin can cancel it. A cancelled change stays in the history. A pause does not move a date the admin chose. | Owner (confirmed 25 Oct 2026) |
| ADM-SUB-09 | There is no proration. The first billing period and a plan change are not prorated: the amount is the plan's price for the period. | Owner |
| ADM-SUB-10 | A subscription's interior care day can be **Custom** instead of a weekday, for a customer whose cars take turns for interior care. A free-text note says whose car's turn it is. The value and the note are stored and shown. The Interior entitlement replaces the rotation: a Custom subscription is a normal case that is owed one Interior for each service week, and the note stays informational (SCHR-INT-25). The customer cannot choose Custom. | Owner (updated 5 Nov 2026) |
| ADM-SUB-11 | On a vehicle that has **no subscription** (for example one loaded from a sheet without plan details), the admin can **set up a subscription**: choose an active plan, the cutoff, the interior care day if the plan has interior care, and an optional first service date (default today). There is no payment status to choose (ADM-CUS-06). It starts as **Activating** with the first plan payment, as for a new vehicle (ADM-SUB-01). A vehicle that already has a subscription cannot be set up again. | Owner and Derived |

## 3. Crew

### 3.1 Onboard crew (items b, c, e)

| ID | Requirement | Status |
|---|---|---|
| ADM-CRW-01 | The admin can onboard one or more crew members. Several can be added in one session, one after another, without leaving the screen. | Owner (item b) |
| ADM-CRW-02 | Details for each crew member: name, mobile number (at most 10 digits can be typed), society, role (Manager, Member or Trainee, required) and working hours. | Owner (mobile entry: 5 Nov 2026) |
| ADM-CRW-03 | The admin can change a crew member's role at any time, including assigning the Manager role to a crew member. | Owner (item c) |
| ADM-CRW-16 | One or more crew members can be given the Manager role, when they are onboarded or later. A society can have several Managers. | Owner |
| ADM-CRW-17 | Onboarding a crew member creates their login with the Crew role, so they can use the app as soon as they are onboarded. The login ID is the crew member's mobile number. A password is generated automatically (the first 3 letters of the name, 4 random digits and `$`). Passwords are never sent by SMS or WhatsApp: the app shows the login ID and the password to the admin once, with a Copy button, and the admin gives them to the crew member outside the app (CRW-ACC-05 in the crew file). | Owner |
| ADM-CRW-18 | The admin can reset a crew member's password. A new password is generated in the same format and shown to the admin once, as at onboarding (ADM-CRW-17). The old password stops working at once. Crew cannot change their own password or login ID (CRW-ACC-06 in the crew file). The admin can also unlock a crew login that is blocked after wrong attempts (CRW-ACC-07); unlocking or resetting ends the block at once. | Derived |
| ADM-CRW-04 | Working hours are set during onboarding for every crew member, whatever their role. For each day of the week the admin marks the day as working or off and sets a start time and an end time. Each Member or Manager has a reporting time and a first-job time. They follow the site values until the admin sets a value for that crew member, and clearing it returns the crew member to the site value (SCHR-PAR-04, SCHR-PAR-05). A job never starts before the later of the first-job time and the start of the window. The site's weekly off is a day off for every crew member (SCHR-PAR-02). Each Member or Manager also has one home zone (ADM-REF-08). | Owner (item e), Owner (updated 5 Nov 2026) |
| ADM-CRW-05 | The admin, and a Manager for crew in their society (CRW-MGR-05), can edit working hours later. The change applies to dates from then on. | Derived |
| ADM-CRW-06 | A mobile number can belong to only one crew member, because it is their login ID. | Derived |
| ADM-CRW-07 | The admin can see the crew list with each person's society, role, working hours and upcoming exceptions, and can search and filter it by society. | Derived |
| ADM-CRW-13 | Every crew member belongs to exactly one society at a time. The admin can move a crew member to another society (ADM-CRW-22). | Owner (18 Oct 2026) |
| ADM-CRW-14 | Trainees count as zero capacity. They appear in the crew list but add nothing to capacity, and the scheduler does not assign visits to them directly. A Trainee gets the jobs of the Member they are paired with (ADM-CRW-19). | Owner |
| ADM-CRW-19 | Every Trainee is paired with a Member of the same society. The admin chooses the Member when onboarding the Trainee and can change it later. A Member can have more than one Trainee, and a Trainee has exactly one Member. Changing a Trainee's role to Member, or a Member's role while Trainees are paired with them, requires pairing to be fixed first. | Owner and Derived |
| ADM-CRW-20 | A Manager can also perform the actions in section 3a of the crew file for crew in their society: see the society's schedule, mark a job Could not complete or skipped, reassign a job, add exceptions, and edit crew working hours. These are recorded with the Manager's name and the time, like admin actions (ADM-SCH-19). | Owner |
| ADM-CRW-21 | The admin can manage a crew member's signed-in sessions. For a crew member the admin sees each active session with its device name, platform, app version and last-active time. The admin can sign out one session or all of that crew member's sessions. The crew member is signed out at once and sees the sign-in screen the next time the app contacts the server. Sessions also end when the crew member is deactivated or their password is reset (CRW-ACC-11). Each sign-out is recorded with the admin and the time. | Owner |
| ADM-CRW-22 | The admin can change a crew member's society from a date the admin picks, which is today or a later day. The society is a dated record: each stay in a society is kept with its start date and ends the day before the next one starts. Earlier stays are never changed and a past date cannot be chosen. The crew member's details page shows the history of stays. A move that has not started yet can be cancelled, and only one move can be waiting at a time. | Owner (18 Oct 2026) |
| ADM-CRW-23 | When a move takes effect, the crew member's open jobs from that day on in the old society go back to the Needs scheduling list (ADM-CRW-12); started and finished jobs and earlier dates stay as they were. From then on the scheduler counts the crew member in the new society. A Trainee being moved on their own is given a Member of the new society to pair with. When a Member is moved, the Trainees paired with them are moved too, to the same society on the same date, and stay paired with that Member; the Society card tells the admin this. Cancelling the Member's waiting move cancels the Trainees' moves with it. If one of those Trainees already has a move waiting, the Member's move is refused until it is cancelled. A Member who has a move waiting cannot be chosen as a Trainee's Member. | Owner (18 Oct 2026) |
| ADM-CRW-24 | In the web portal, each row of the crew list has an edit icon that opens that crew member's page. The crew member's page shows its sections as tabs, one at a time: Details, Society, Role and pairing, Working hours, Exceptions, Account and Sessions. The open tab is kept in the address (for example `/crew/<id>?tab=society`), so a link or a reload returns to it. | Owner (18 Oct 2026) |
| ADM-CRW-25 | A crew member can have more than one working slot on a day, for example 05:00 to 13:00 and 17:00 to 19:00. Slots on a day must not overlap or touch. The scheduler places each job inside one slot and counts the total of the slots as capacity. Working hours are mandatory: the admin enters the hours of every new crew member, Monday to Sunday. Nothing is copied or assumed. The society's working slots (Cleaning-External and Cleaning-Internal, joined where they overlap, weekly off left out) are shown as a suggestion that the admin may accept or change. The break (09:30 to 10:00 by default) can be changed for one crew member or for a date range (SCHR-BRK-05, SCHR-BRK-06). The admin can edit the slots, add more later, or reset them to the society's slots. | Owner (18 Oct 2026), Owner (updated 5 Nov 2026), Owner (updated 7 Nov 2026) |
| ADM-CRW-26 | In the web portal crew list, the "Working days/hrs" column shows the days worked this week (Monday to Sunday) as letters, for example M, T, W, T, F. A day off, or a day off for the whole day by an exception (Sick, Leave), is left out. A day with a partial exception (Late start) is shown in a different colour. On hover the column lists each day with its hours and slots, the partial days with the exception detail, and the days left out by an exception. | Owner (18 Oct 2026) |
| ADM-SITE-01 | The web portal has a master Site selector at the top left of the sidebar. The admin works on one society at a time, and the Customers, Subscriptions, Crew, Schedule, Working slots, Capacity, Payments, Add-ons, Complaints, Feedback and Operations pages all show only the chosen site. The choice is remembered in the browser. Master data that applies to every site is kept apart under "All sites": societies, base plans, base services, base checklists and the add-on catalogue (Master data), Settings and Features. Working slots belong to a site and have their own page. The **Audit trail** is a site page: it sits under "This site" and shows the chosen site's changes and those marked "All sites" (ADM-SET-09). | Owner (18 Oct 2026); Audit trail placement Derived |
| ADM-CRW-15 | The admin can deactivate a crew member who has left. A deactivated crew member no longer counts in capacity or the scheduler, and cannot sign in. Their past visits and records stay. | Derived (in MVP) |

### 3.2 Exceptions (item f)

| ID | Requirement | Status |
|---|---|---|
| ADM-CRW-08 | The admin can mark an exception for a crew member on one date or a date range. Types: **Sick**, **Leave**, **Late start**. | Owner (item f) |
| ADM-CRW-09 | Sick and Leave remove the crew member from the whole day. Late start removes the crew member until the start time the admin enters for that day. | Derived |
| ADM-CRW-10 | The admin can edit or remove an exception. | Derived |
| ADM-CRW-11 | Capacity is recalculated as soon as an exception is saved, edited or removed, so it is always accurate (section 5). | Owner |
| ADM-CRW-12 | If an exception affects visits that are already scheduled, the app lists the affected visits so the admin can reassign them. On a frozen schedule the exception removes the crew member's visits without the code (ADM-SCH-29). The visits then go to the Needs scheduling list (ADM-SCH-28), and reassigning them needs the code (ADM-SCH-17) or happens automatically if a crew member fits (ADM-SCH-27). | Derived |
| ADM-CRW-27 | At the top of the Crew page the admin sees summary tiles: total crew, Active, Inactive, Locked, with exceptions, and how many Managers, Members and Trainees. Choosing a tile filters the list. Tabs for All, Managers, Members and Trainees sit above the list. The page can be shown as a table or as tiles, as in ADM-CUS-26. | Owner |

---

## 4. Services and working slots (item d)

| ID | Requirement | Status |
|---|---|---|
| ADM-SVS-01 | There are three services: **Cleaning-External**, **Cleaning-Internal** and **Deep Spa**. In the customer app Cleaning-External and Cleaning-Internal appear as the visit types Exterior and Exterior + Interior, and Deep Spa appears as the Full spa add-on. Every visit includes one Cleaning-External. The plan's Interior entitlement adds Cleaning-Internal: one for each service week, planned on any working day (SCHR-INT-06). The interior care day is only a preference (SCHR-INT-05). Deep Spa is not part of the plan: it is an add-on that existing customers buy separately (section 9a of the customer file, ADM-ADD). A Cleaning-Internal missed for an operational reason (car, keys, capacity, skipped by operations) is owed and carries forward to a later day. A service week that is fully paused is waived. A one-day customer skip leaves it pending until the week ends (SCHR-INT-21). Each service is a **separate job**, with its own job card, checklist, proof and completion (CRW-SCH-05 in the crew file). The customer's visit is Completed when all of its jobs are done. | Owner (updated 5 Nov 2026) |
| ADM-SVS-02 | A working slot is a start time and an end time on chosen days of the week, during which that service can be done. Every working slot belongs to one society. | Owner |
| ADM-SVS-03 | A service can have several independent working slots in a society, for example 5 to 8 AM and 4 to 6 PM. | Owner |
| ADM-SVS-04 | The admin can add, edit and delete working slots for every service, for each society. | Owner |
| ADM-SVS-05 | Default working slots: **Cleaning-External**: 5 AM to 11 AM, every day except the weekly off. **Cleaning-Internal**: 5 AM to 11 AM, every day except the weekly off. **Deep Spa**: every day except the weekly off, at any time of day. The weekly-off weekday is a site setting and is Wednesday by default (SCHR-PAR-03). A weekday with no slot is a day off for all three services (SCHR-PAR-02, SCHR-PAR-16). The default applies to new sites. An existing site changes only when the admin saves the change or the owner approves a data update. | Owner (updated 5 Nov 2026) |
| ADM-SVS-06 | A new society starts with the default working slots, which the admin can then edit. | Derived |
| ADM-SVS-07 | A slot's end time must be after its start time, and two slots of the same service cannot overlap on the same day in the same society. | Derived |
| ADM-SVS-08 | Changes to working slots apply to scheduling from then on. A frozen schedule is not changed by them. | Derived |
| ADM-SVS-09 | Planning durations: **Cleaning-External** 30 minutes, **Cleaning-Internal** 30 minutes, and **Deep Spa** 2 hours (120 minutes). The admin can edit each one. A visit with both cleaning jobs takes 60 minutes of work, and no travel minutes are added (SCHR-HARD-06). These apply to every vehicle category for now. The default changes from 20 to 30 minutes for new sites. A job already planned at 20 minutes keeps its length until it is planned again, and an existing site changes only when the admin edits the duration or the owner approves a data update (SCHR-PAR-06, SCHR-PAR-07). | Owner (updated 5 Nov 2026) |
| ADM-SVS-10 | The scheduler plans all three services with these durations (ADM-SVS-09), each as its own job. Cleaning-External is due on every working day. Cleaning-Internal is due by entitlement: one for each service week for a subscription whose plan includes interior care, planned on any working day and not only on the interior care day (SCHR-INT-01, SCHR-INT-06). A Deep Spa job is planned when a customer buys it, as an add-on or as a standalone service (ADM-ADD-10), on the date and finish-by time proposed (ADM-SCH-30). | Owner (updated 5 Nov 2026) |
| ADM-SVS-11 | The page is called **Site Working slots**. It lists the working slots of every service together, with tabs for All and each service, as a table or as tiles (ADM-CUS-26). The admin can add, edit and delete a slot from either view, as before. | Owner |

---

## 5. Capacity

Capacity is worked out for each society, because crew and working slots belong to one society each.

| ID | Requirement | Status |
|---|---|---|
| ADM-CAP-01 | The admin can see the capacity for each society and date: the crew hours available that day, from every counted crew member's working hours minus their exceptions, and what fits in it, counted in minutes: each job counts its set duration, 30 for a Cleaning-External or a Cleaning-Internal and 120 for a Deep Spa by default (ADM-SVS-09). The break is not capacity: a day's capacity is the cleaners' windows minus the break (SCHR-BRK-08). The time between the first-job time and the Interior-earliest time (05:30 to 07:00 by default) that stays free is shown as available for onboarding (SCHR-EXT-09). | Owner (items e, f), Derived (v1.2 additions) |
| ADM-CAP-02 | Trainees add zero (ADM-CRW-14). Members and Managers both count in full. | Owner |
| ADM-CAP-03 | Next to capacity the admin sees the demand for that date in the same minutes: one Cleaning-External for each active vehicle (after skips and pauses), plus the Cleaning-Internal and Deep Spa jobs due that day, and how many of them have been scheduled so far. | Derived |
| ADM-CAP-04 | Dates where demand is higher than capacity are marked, so the admin can act before scheduling. | Derived |
| ADM-CAP-05 | The capacity figure is always current. It updates immediately when crew are added or deactivated, working hours change, or an exception is saved. | Owner |
| ADM-CAP-06 | On the Capacity Utilisation page, hovering over a date's "Crew available" shows each counted crew member with their hours and slots for that date. Hovering over "Demand" shows the work due that date by service, with the number of jobs and the hours, and marks add-on work. | Owner (18 Oct 2026) |
| ADM-CAP-07 | The page is called **Capacity Utilisation**. At the top the admin sees summary tiles for the dates shown: days shown, days over capacity, crew hours available, demand, scheduled hours and overall use. The page no longer lists the crew; crew hours and exceptions are on the Crew page. The page has no tile view. | Owner |
| ADM-CAP-08 | A weekday on which the society has no working slot for a service (ADM-SVS-02) is a day the site is off for that service: its demand that day is 0. It does not count towards over capacity (ADM-CAP-04), and the scheduler creates no jobs and no Needs scheduling entries for it. Capacity and the scheduler use the same rule. A service with no working slot at all in the society is not filtered, and a society with no slots keeps the standard hours (ADM-CRW-25). Re-run jobs that already exist stay. The weekly-off weekday (Wednesday by default) is such a day for all three services, and a crew member's own hours on that day add no capacity (SCHR-PAR-16, SCHR-HARD-07). | Owner (04-Nov-26), Owner (5 Nov 2026) |

---

## 6. Payments (item h)

| ID | Requirement | Status |
|---|---|---|
| ADM-PAY-01 | The admin can see a list of payments and filter by status (Not Due, Due, Due today, Over due, Initiated, Paid), customer, vehicle and cycle end date. | Derived |
| ADM-PAY-02 | The admin can update the status of any payment: **Approve** an Initiated payment (it becomes **Paid**), **Reject** it, or set it to **Initiated** or **Paid** directly. Setting a payment back to Not Due, Due, Due today or Over due means no payment counts for the cycle, and the status follows the cycle dates (PAY-14 in the customer file). | Owner (item h); date-based statuses: Owner (4 Nov 2026) |
| ADM-PAY-03 | When the admin approves a payment, the status becomes **Paid** and the customer gets "Payment received" for the cycle dates and the vehicle that were paid (PAY-08, PAY-09 in the customer file). | Owner |
| ADM-PAY-04 | The admin can record a payment for a customer who paid offline or in person, without the customer marking it Initiated first. | Derived |
| ADM-PAY-05 | Every status change records which admin made it and when. | Derived |
| ADM-PAY-06 | The backend works out each plan payment's status from the cycle dates and the payment records (PAY-14 in the customer file) and refreshes it in a daily job at 2:00 IST (ADM-PAY-14). The payment is due on the cycle's end date. A pause, a skip, a credit or an early or late payment does not move the end date (PAY-15). An add-on payment is created Due on the day the add-on is requested and becomes Over due immediately after its service is completed, if the payment is not yet received (ADM-PAY-13). | Owner (4 Nov 2026) (replaces the rule that created the payment 7 days before renewal and moved its due date with a pause) |
| ADM-PAY-07 | The admin can move a payment back from Initiated or Paid to Not Due, Due, Due today or Over due (the date rule decides which), for example when the customer marked it paid but the money did not arrive, or Paid was set by mistake. Reject does the same and sends the customer "Your last payment failed". The renewal reminders still ahead then resume (NOTIF-05 in the customer file). The customer is not sent a new notification and sees the new status in the app. The change is audited (ADM-PAY-05). | Owner and Derived |
| ADM-PAY-08 | When a payment is **Paid**, the admin can generate a GST invoice for it. The customer can view it in billing history (SUB-06 in the customer file). The invoice fields come from the invoice settings (ADM-SET-04). | Owner |
| ADM-PAY-09 | The invoice number is **PRV** + the month + the year as two digits (YY) + the last 4 digits of the customer's mobile number + 4 random digits. The month is two digits (01 to 12). Example for October 2026, mobile ending 4321: `PRV10264321` followed by 4 random digits such as `8052`. The backend generates it and makes sure it is unique, drawing new random digits if the number already exists. | Owner |
| ADM-PAY-10 | Every payment has a type: **Plan** or **Add-on**. The payment list can be filtered by type, and the status rules, audit and GST invoice (ADM-PAY-02 to ADM-PAY-08) work the same for both. | Derived |
| ADM-PAY-11 | When a customer marks a plan or add-on payment as paid and its status becomes Initiated, the admin is alerted (ADM-ACC-09). | Owner |
| ADM-PAY-12 | At the top of the Payments page the admin sees summary tiles: all payments, and for each status (Not Due, Due, Due today, Over due, Initiated, Paid) the number of payments and their total in rupees, for the chosen site. Choosing a status tile filters the list to that status. | Owner |
| ADM-PAY-13 | An add-on stays charged separately from the plan, as today (ADM-PAY-10). Its payment becomes **Due** if it is not paid by the scheduled service date, and **Over due** if the service is completed and the payment is not yet received. This does not make a subscription Inactive (ADM-SUB-03). | Owner |
| ADM-PAY-14 | A job runs every day at 2:00 IST. It refreshes the payment statuses (PAY-14, PAY-19 in the customer file), creates the payment record for a new cycle, and makes a subscription Inactive when its plan payment has been Over due for 7 days (ADM-SUB-03), which alerts the admin (ADM-SCH-24). This job does not send reminders: the renewal reminders (NOTIF-05) are sent by a separate daily job, at the same time as today (10:00 IST). | Owner (4 Nov 2026); reminder send time: existing, not changed |
| ADM-PAY-15 | For a customer loaded from a sheet, the admin enters the payments already made, including past cycles, in the portal (ADM-PAY-04). The status of each cycle comes from those records and the cycle dates. The system does not guess a payment. | Owner (4 Nov 2026) |

---

## 7. Scheduling (items j, k)

Scheduling turns the customers' services and the crew's capacity into a plan of who does which visit, and when.

### 7.1 Run the scheduler (item j)

| ID | Requirement | Status |
|---|---|---|
| ADM-SCH-01 | The admin starts scheduling for a chosen society, or all societies, and a date range. Nothing is scheduled until the admin starts it. | Owner (item j) |
| ADM-SCH-02 | For each society the scheduler uses only that society's crew, working slots and customers. | Owner |
| ADM-SCH-03 | The scheduler plans all three services, each as its own job with its own duration (ADM-SVS-09, ADM-SVS-10). | Owner |
| ADM-SCH-04 | The scheduler uses: each customer's schedule settings (cutoff time, interior care day, skips, pauses), add-on requests, the working slots of each service, every counted crew member's working hours, and crew exceptions. It also uses the Interior entitlements, the zones (each vehicle's zone and each cleaner's home zone), the break, the reporting and first-job times, the Interior-earliest time, the weekly off and the cutoff policy (SCHR-PAR, SCHR-INT, SCHR-ZONE, SCHR-BRK). Every value is read from configuration (SCHR-CFG-01). Trainees are never assigned directly: they get the jobs of their paired Member (ADM-CRW-19). | Owner and Derived |
| ADM-SCH-05 | The scheduler follows the ordered rules of the scheduler requirements file (SCHR-HIER-03, SCHR-HIER-04). The hard constraints are never broken. Every active car gets one Exterior on every working day, planned before any Interior (Pass A). Then come the home zones, the weekend cutoffs, the usable early capacity and the break. Interiors are planned after that, oldest service week first (Pass B). It no longer aims at the greatest use of the crew's capacity on its own. | Owner (updated 5 Nov 2026) |
| ADM-SCH-06 | The result is a draft schedule: for each visit, the date, the crew member and a time inside a working slot. | Derived |
| ADM-SCH-07 | A visit should finish by the customer's service cutoff time (the Customer cutoff). On the strict days (Monday, Tuesday, Thursday and Friday by default) the cutoff is a hard limit for Exterior and Interior. A job is never placed to finish after it: an Exterior that cannot fit is left Unscheduled with the reason and the cutoff time, and an Interior is deferred and stays pending (SCHR-CUT-01 to SCHR-CUT-04). On Saturday and Sunday the cutoff is flexible: the scheduler prefers to meet it, and a job that ends after it is flagged Late (SCHR-WKE-01, SCHR-WKE-06). The customer can choose any cutoff time (ONB-16), so the scheduler does not assume it can be met. When the admin places a job by hand after a weekday cutoff, the screen warns, the job is marked Late and the breach is listed in the exception report. The admin may go ahead (SCHR-CUT-05). | Owner (updated 5 Nov 2026) |
| ADM-SCH-08 | Visits that cannot be placed, for example because capacity is short, are listed as **Unscheduled** with a reason from a fixed list: no cleaner, shift too short, weekday cutoff, weekly off, capacity short, break kept, Interior before 07:00, or entitlement already used (SCHR-OUT-04). The run also reports the shortfall in cars and minutes (SCHR-EXT-04). | Derived, Owner (updated 5 Nov 2026) |
| ADM-SCH-09 | One scheduler run covers one period. The period is a week by default, and the week starts on Sunday. The service week that the Interior entitlement uses is separate: it runs Monday to Sunday and has its own setting (SCHR-PAR-13). The planner works out the service week of each day itself and plans the days in date order (SCHR-HIER-01). The admin can switch it to Daily or Monthly in Preferences (ADM-PRF-01). | Owner (updated 5 Nov 2026) |
| ADM-SCH-10 | Dates beyond the scheduled week have no crew assignment yet. The customer calendar shows the visits expected from the subscription for those dates (CAL-01 in the customer file). | Derived |

### 7.2 Review, change, re-run, freeze (item k)

| ID | Requirement | Status |
|---|---|---|
| ADM-SCH-11 | A schedule is either **Draft** or **Frozen**. A new schedule starts as Draft. | Derived |
| ADM-SCH-12 | The admin can review a draft schedule by day, by crew member and by customer or society. | Owner |
| ADM-SCH-13 | In a draft the admin can make changes by hand: move a visit to a different crew member or time, swap two visits, remove a crew assignment, and assign an Unscheduled visit. | Owner |
| ADM-SCH-14 | The admin can re-run the scheduler on a draft any number of times. A re-run always keeps the changes made by hand. | Owner |
| ADM-SCH-15 | A re-run can also suggest improvements that make better use of capacity. The admin chooses which suggestions to apply. Nothing is changed without the admin's choice. | Owner (suggestions) and Derived (admin chooses) |
| ADM-SCH-16 | The admin can **freeze** a draft. A frozen schedule cannot be edited. | Owner |
| ADM-SCH-17 | To add or move work in a frozen schedule (removals are exempt, ADM-SCH-29, and so is a Manager's reassignment of a job, CRW-MGR-03), the admin must enter the **secret code**, which unfreezes it. The admin then edits, can re-run, and freezes again. | Owner |
| ADM-SCH-18 | The secret code is the word **unfreeze**. A wrong code does not unfreeze the schedule. The code is checked by the backend. | Owner |
| ADM-SCH-19 | Every freeze, unfreeze, manual change and re-run records which admin did it and when. | Derived |
| ADM-SCH-20 | As soon as a schedule is frozen, each crew member can see their assigned schedule as a stack of cards, one for each assigned car. They can view it day by day, or for everything that has been scheduled so far. The details are in the crew requirements. Customers see the assigned crew member and time once the visit has been assigned (CAL-10 in the customer file). Until then they see only their own cutoff time. | Owner |
| ADM-SCH-21 | If a customer skips or pauses after a schedule is frozen, the change applies to the frozen schedule automatically, without unfreezing: the visit is removed, and the admin is alerted (ADM-ACC-09). | Owner |
| ADM-SCH-22 | If a customer changes a cutoff time after a schedule is frozen, the new cutoff time is saved as a request to the admin. The app does not move the assigned visit. The admin is alerted (ADM-ACC-09) with the customer, the vehicle, the old and new cutoff time, and the assigned crew member and time. | Owner |
| ADM-SCH-23 | The admin then chooses how to deal with the request: run the scheduler to fit it in, or change the schedule by hand, and then freeze again. Changing a frozen schedule needs the secret code (ADM-SCH-17). | Owner |
| ADM-SCH-24 | The admin alerts in MVP are: a skip or pause after a freeze (ADM-SCH-21), a cutoff time request (ADM-SCH-22), an add-on cancellation or change after a freeze (ADM-SCH-31), a job the crew could not complete (ADM-CNC-04), a visit auto-assigned after a freeze (ADM-SCH-27), a visit that needs scheduling (ADM-SCH-28), a subscription that became Inactive automatically (ADM-SUB-03), a payment marked Initiated (ADM-PAY-11), and a new complaint (ADM-CMP-08). Each reaches the admin as described in ADM-ACC-09. The bell and the phone push cannot be switched off, but the emails can. | Owner and Derived |

### 7.2a Freeze cutoff time

| ID | Requirement | Status |
|---|---|---|
| ADM-SCH-25 | A schedule is frozen once, before its first day. The **freeze cutoff time** is **8 PM the day before the first day** of the schedule's period (for a weekly schedule, 8 PM the day before the week starts). After the freeze every change is handled as a late change (ADM-SCH-27 to ADM-SCH-29). The customer's skip and pause deadline is 9 PM (SCHED-01), so a skip or pause made after the freeze is removed from the frozen schedule automatically (ADM-SCH-21). | Owner |
| ADM-SCH-26 | A job scheduled again after a Missed outcome (ADM-CNC-06) goes into the next day's schedule. If that schedule is frozen, it is assigned automatically as in ADM-SCH-27, with no code, or goes to the Needs scheduling list if no crew member fits (ADM-SCH-28). If that schedule is still a draft, it is placed with the other jobs. A Cleaning-Internal job that was not done because the car or the keys were not available is not rescheduled by the admin. It is deferred: its entitlement goes back to pending with its original service week, and the scheduler plans it again in the next feasible slot (SCHR-DEF-01 to SCHR-DEF-03, SCHR-DEF-05). | Owner (updated 5 Nov 2026) |
| ADM-SCH-27 | After a schedule is frozen, a visit that needs a crew member (a new customer or vehicle, an un-skip, an ended pause, or a reactivated subscription) is **assigned automatically** without unfreezing. The system picks a counted crew member of the same society who has spare capacity, the visit's slot allows it and no other job overlaps, and gives the earliest time before the customer's cutoff time. The admin is alerted (ADM-ACC-09) and the crew member gets a push notification. | Owner |
| ADM-SCH-28 | If no crew member fits, the visit goes to a **Needs scheduling** list and the admin is alerted (ADM-ACC-09). The admin then adds it by hand (ADM-SCH-13 and ADM-SCH-17) or re-runs the scheduler. | Derived |
| ADM-SCH-29 | **Removing** work from a frozen schedule does not need the secret code: a visit skipped by operations, a crew exception, a crew deactivation, or a visit removed by the customer's skip or pause. The visits left without a crew member go to the Needs scheduling list (ADM-SCH-28). Adding or moving work by hand needs the code. | Owner and Derived |
| ADM-SCH-30 | An add-on request (Deep Spa) is planned as a job of its own duration on the date the customer proposed, with the customer's finish-by time, in the same way as other jobs (ADM-SCH-03). It does not wait for payment (ADM-ADD-08). If it cannot be placed it goes to the Needs scheduling list (ADM-SCH-28). | Owner |
| ADM-SCH-31 | If a customer cancels an add-on after the schedule is frozen, the job is removed from the schedule automatically, without unfreezing, and the admin is notified (like ADM-SCH-21). If the customer changes the date or finish-by time after the freeze, the change is saved as a request to the admin (like ADM-SCH-22). The admin deals with it as in ADM-SCH-23. | Owner and Derived |
| ADM-SCH-32 | In the web portal, the Schedule page shows its sections as tabs: Board, Needs scheduling, Skipped and paused, Cutoff requests and Draft improvements. Each tab works on the day chosen at the top of the page (ADM-SCH-35), and Needs scheduling, Skipped and paused and Cutoff requests show that day's count. On the Board, a crew member who cannot work on the chosen day (a day off, Sick or Leave, or a Trainee) is greyed out, placed last and takes no job; a job dropped there is refused and the reason is shown. A job dropped on a member goes only into time that member works (their slots, after a Late start). Hovering a crew member's name shows how the jobs were allocated: the day's slots and the reason, the minutes booked against the minutes available, the jobs by service and the scheduler's notes. Run is not a tab: it is a **Run** button in the top bar of the page that opens a dialog for the period (the dialog closes when the run starts and the button shows Running… until it ends). | Owner (18 Oct 2026) and Derived, Owner (5 Nov 2026) |
| ADM-SCH-33 | In the web portal, the Board shows the chosen day in one of three views. **Cards** is the default and is where jobs are changed: a column for the jobs with no crew member (Unscheduled), then one column for each crew member with that member's jobs and free slots in time order, the time between slots, and the use of the member's time as a percentage and in hours and minutes (used and free). Each card shows the start and end time, the service code (EXT, INT or SPA), the vehicle number, the parking place (basement and number) and the finish-by time. The admin drags a card onto a free slot, where it starts at the point it is dropped (to 5 minutes), or between two cards, where it takes the first free time after the card above it, inside that member's slots. A slot too short for the job refuses it and says why. Dropping a card on Unscheduled takes it off its crew member, after a confirmation. Clicking a card opens it to set an exact crew member and time. **Timeline** is view only: a compact Gantt chart with one thin row for each crew member against an hour ruler that spans the day's working hours, each job a small block at its start time as wide as its duration. Hovering a block, or moving to it with the keyboard, shows its details. **Table** (5 Nov 2026) lists every job of the day, with the unscheduled ones, as a row: time, crew member, vehicle number and model, customer, parking place, service, minutes, finish-by time, status, and its flags and reason. A click on a heading sorts by it (a second click reverses it); the first order is by crew member and then time, with the unassigned first. Clicking a row opens the job to move it; the table itself changes nothing. It shows the count, and an Export CSV button saves the rows shown (text that a spreadsheet could run as a formula is quoted). **Search and filters (5 Nov 2026):** one search box serves all three views and finds a job by vehicle number, parking place, customer, crew member, vehicle model or service; several words must all be found. On Cards and Timeline the jobs that do not match are dimmed and the first match is brought into view; on Table they are left out. Chips keep only one kind of work (EXT, INT, SPA), one status, Late or By hand, and a crew picker shows only the chosen crew members' lanes and rows. The page shows no scroll bars; a small arrow shows where there is more to see. **Cards (5 Nov 2026):** a Compact, Standard or Detailed choice sets how much a card shows (Detailed adds the customer and the vehicle model), and it is remembered in the browser. While a card is held, the columns that can take it show green, the ones that cannot show red, and a free slot too short for it says so. A move shows on the Board at once and is put back with the reason if it is refused; a toast offers Undo. With a card in focus, Alt and the up or down arrow move it 5 minutes within its own column, only into free time. **Focus and own tab (5 Nov 2026):** a Focus button (or the F key) opens the Board alone in a window-sized dialog, with the day, the views, the search, the chips and the Board; the strip of days starts folded there, and Escape goes back to the page. The job dialog and the confirmations open over it. A New tab link opens the Board alone in its own browser tab, signed in and on the same site, day and view, with no navigation or tabs, so it can be kept on a second screen; each window shows a move made in the other when it is next used. Neither shows Run or Reassign crew day. **Lanes (5 Nov 2026):** the Unscheduled column stays at the left while the crew lanes scroll, so a card can always be dropped on it. A crew member's lane can be folded to a thin strip (name, jobs and use of time), which still takes a dropped card at its first free time, and is unfolded with one click; the folded lanes are remembered in the browser. The crew picker can also leave out the crew members who are off that day. Dragging the background or a column heading pans the Board sideways, and the mouse wheel over a heading does the same. **Room (5 Nov 2026):** the page uses the whole width of the window and the Board fills the height under the top bar, so only the lanes scroll and the page itself does not; the title, the day and the schedule actions share one slim bar, the explanation of how to drag is a small note icon instead of a line of text, and a day with many crew members scrolls sideways under the arrows. **Scheduling rules v1.2:** a break is shown as a block that cannot take a job (SCHR-BRK-09). A job moved by hand against a rule is warned about, allowed and flagged (SCHR-HIER-08). The grid step comes from a setting (SCHR-CFG-01), and card heights follow the job length, which is 30 minutes by default. | Owner (18 Oct 2026) and Derived, Owner (5 Nov 2026), Derived (v1.2 additions) |
| ADM-SCH-34 | On the Board, each job shows its current status, in both views. A Completed job shows a green tick, a job that Could not complete a red cross and a dashed red edge, and a job In progress a blue ring and a pulsing dot; the status is also written on the card. The card's colour is the kind of work (5 Nov 2026): exterior green, interior blue, Deep Spa purple, so the kind stays visible whatever the status. Chips for EXT, INT and SPA keep only that kind bright; pressing one again shows all. Above the board, the chosen day's jobs are counted by status (Scheduled, In progress, Completed, Could not complete). Choosing a status keeps only those jobs bright; choosing it again shows all. The job dialog shows the status. | Owner and Derived (the colours by kind, 5 Nov 2026) |
| ADM-SCH-35 | The Schedule page is led by one chosen day. At the top, the admin steps a day back or forward, picks any date, or clicks a day in a strip that runs from 30 days back to the last scheduled day. Each day in the strip shows its schedule's status (Draft, Frozen or no schedule) and a mark when it has jobs that need scheduling or cutoff requests. Today is chosen at first, or the next scheduled day. Under the strip, the chosen day's schedule shows its status, the period it covers, its freeze time and Freeze or Unfreeze; freezing applies to every day of that schedule. Every tab shows and changes only the chosen day; Run schedules the period that contains it. A tab that lists items says how many more are on other days, with a link to each of those days. Running the scheduler does not hide the days of other schedules. The strip of days can be folded away with the Hide days button (Show days brings it back), leaving the arrows and the date field in the bar; the choice is remembered in the browser for the admin. | Owner (18 Oct 2026) and Derived, Owner (5 Nov 2026) |
| ADM-SCH-36 | Skipped and paused jobs are not on the Board, its counts or its Unscheduled column. The Board says how many of the chosen day's jobs are skipped or paused and links to the **Skipped and paused** tab. That tab lists them for the chosen day, with the vehicle, customer, service, type (Skipped or Paused) and why: skipped or paused by the customer or the admin (with the pause dates), skipped by operations, skipped by a crew manager, or no longer due. It can show skipped only or paused only. | Owner |
| ADM-SCH-37 | The admin can move one scheduled service to any date. The visit keeps its original date and its revised date, and both are shown on the visit and in its history. | Owner (confirmed 25 Oct 2026) |
| ADM-SCH-38 | Each crew member has an ordered daily queue of jobs (CRW-SCH-14). The admin can reorder the queue or unlock the next job. A reason is mandatory. Each override is recorded in the audit (ADM-SET-07) with the admin and the time, and the crew member gets a push notification (CRW-NOT-06). | Owner |
| ADM-SCH-39 | The admin can reassign all of one crew member's jobs for a date or date range to a replacement crew member in one action. Each moved job is recorded. | Owner (confirmed 25 Oct 2026) |
| ADM-SCH-40 | The admin can mark every service of a society on a date or date range as Missed or Cancelled in one action, with one reason for all. Each service keeps the reason. | Owner (confirmed 25 Oct 2026) |
| ADM-SCH-41 | A vehicle's schedule is one of two patterns and repeats automatically every billing cycle. **Weekly:** the admin chooses the weekdays for Exterior and the weekdays for Interior. **Cycle:** the admin chooses day numbers inside each 30-day billing cycle, with a count of Exterior-only days and a count of Exterior + Interior days. The combined Exterior + Interior day can fall on any weekday. The intent is the owner's (23 Oct 2026). The model details are Derived: an Interior weekday is also an Exterior weekday, day numbers count from the cycle's first day, and the counts must match the days chosen. A subscription with no pattern keeps today's default: Exterior every day and Interior on its interior care day. A Weekly pattern with six weekdays gives a rest day. The Cycle position moves with paused days, as the billing cycle does. The scheduler and the calendar read the same rule. Only the admin sets a pattern for now (section 13, question 2). Under the scheduling rules v1.2, the Interior weekdays of a pattern feed the car's preferred days only (a tie-break). They do not override the Interior entitlement (SCHR-INT-26). The pattern is kept, and the car can have fewer than six Exteriors a week (SCHR-EXT-11). | Owner and Derived |
### 7.3 Preferences

| ID | Requirement | Status |
|---|---|---|
| ADM-PRF-01 | The admin has a Preferences screen. It holds the scheduling period, with three options: **Daily**, **Weekly** and **Monthly**. The default is Weekly, with the week starting on Sunday. Next to the period, a separate setting holds the service week start, Monday by default. It decides the Interior entitlement and does not change the planning period (SCHR-PAR-13). Monthly covers one calendar month. | Owner (updated 5 Nov 2026) |

---

## 8. Complaints, feedback and ratings

These are the admin features the customer requirements already depend on. You confirmed they are all part of the MVP.

### 8.1 Complaints

| ID | Requirement | Status |
|---|---|---|
| ADM-CMP-01 | The admin can see a list of complaints with ID, customer, vehicle, category, linked visit, status and raised date, and can filter by status, society and category. | Owner |
| ADM-CMP-02 | The admin can open a complaint to see its description, photos and the linked visit. | Derived |
| ADM-CMP-03 | The admin can change a complaint's status: **Raised**, **In progress**, **Resolved**. | Owner |
| ADM-CMP-04 | The admin can add an update note to a complaint, for example "Supervisor visit booked". The customer sees it in My complaints. | Owner |
| ADM-CMP-05 | Each status change and each new update note sends the customer a "Complaint update" push notification, if they have it switched on (CMP-04 in the customer file). | Owner |
| ADM-CMP-06 | The team's own target is a reply within 4 hours. It is not promised to the customer (ISS-06 in the customer file). A complaint still in Raised after 4 hours is highlighted in the list. | Derived |
| ADM-CMP-07 | Each status change and note records which admin made it and when. | Derived |
| ADM-CMP-08 | The admin is alerted when a customer raises a complaint (ADM-ACC-09), and again when a complaint is still Raised after 4 hours (ADM-CMP-06). The 4-hour alert is raised at the next daily run of the complaints job, so it can come up to a day late (ADM-OPS-05). The alert email gives the customer's first name, the category, the visit date if one is linked, the start of the description, and a link that opens the complaint in the web portal. Photos are not attached; the admin sees them in the portal. | Owner, changed and Open (5 Nov 2026): the owner to confirm the daily alert |
| ADM-CMP-09 | At the top of the Complaints page the admin sees summary tiles: total complaints, how many are Raised, In progress and Resolved, and how many are overdue. Choosing a tile filters the list. | Owner |

### 8.2 Visits skipped by operations

| ID | Requirement | Status |
|---|---|---|
| ADM-OPS-01 | The admin can mark a scheduled visit or job as skipped by operations, for example when crew are unavailable. The visit shows as Skipped for the customer, who gets a "Service skipped" push notification if they have it switched on (NOTIF-04 in the customer file). | Owner |
| ADM-OPS-02 | The admin can add a reason when skipping a visit. | Derived |
| ADM-OPS-03 | A visit or job skipped by operations does not extend the plan and does not change that month's cost. The renewal date does not move and the customer is not charged extra. This replaces the earlier rule that extended the plan by one day for a skipped Cleaning-External visit (owner decision of 23 Oct 2026, B-01). A skipped Deep Spa add-on is still refunded or rebooked by the admin outside the app. A pause still moves the renewal date (PAUSE-02 in the customer file). | Owner |
| ADM-OPS-04 | Only the admin can skip a visit or job by operations. Crew cannot skip a job. A Manager can skip only when the feature flag **Allow Crew Manager to Skip** (`crew.manager_skip`) is on. It defaults to off (CRW-MGR-02). The customer-facing Skip and Pause stay controlled by the existing flag `customer.skip_pause` (SKIP-10 in the customer file). | Owner |
| ADM-OPS-05 | The portal has a page **Scheduled jobs** under All sites. It lists every scheduled job with a plain-words purpose, its schedule in IST, an on/off switch, the last run, its status, what it did and whether its purpose was achieved. Only the admin can open it and change a switch. Switching a job off asks for confirmation and says what stops. A job that is off does nothing when it is called and is recorded as Skipped. The starting state on every environment is: complaints-overdue and payments-daily on; freeze-due, automatic-planning, renewal-reminders, checkin-notify and mani-retention off. Mani-retention has no schedule on Vercel. Each switch change is written to the Audit log. Turning automatic planning on needs the planning time to be set first (ADM-SET-05). While freeze-due is off, an admin freezes each schedule by hand, because the crew see jobs only on a Frozen schedule. | Owner (5 Nov 2026); the last sentence is Derived |
| ADM-OPS-06 | Crew society moves have no scheduled job. A move that has come due is applied when the crew data is opened or the scheduler loads the society's crew (ADM-CRW-22). | Owner (5 Nov 2026) |
| ADM-OPS-07 | Every call of a scheduled job is recorded with its start, end, duration, result and a short error text, and shown with a status: Success, Failed, Skipped (switched off), Did nothing, Never run, Timed out or Late. A run that never finished is Timed out after 6 minutes. An enabled, scheduled job with no run since its expected time plus 70 minutes is Late. A job that is off is never Late. The Scheduled jobs page shows the last 20 runs of a job. | Derived |
| ADM-OPS-08 | Run records older than 90 days are deleted by the daily payments job. | Derived |
| ADM-OPS-09 | Each run writes one log line with the job, how it was started, the status, the duration and the result, for the host's log. The page shows "Purpose achieved" as a check on live data where the check is cheap (payments-daily, complaints-overdue, freeze-due) and "Not checked" for the other jobs. | Derived |

### 8.2a Visits the crew could not complete

| ID | Requirement | Status |
|---|---|---|
| ADM-CNC-01 | The admin can add, rename, reorder and deactivate the **could-not-complete reasons** the crew choose from (for example car not in the parking spot, car locked, customer did not allow, bad weather, other). A deactivated reason no longer appears for crew, and past records keep it. | Derived |
| ADM-CNC-02 | When a crew member marks a job Could not complete (CRW-CNC-01), the job is **Missed**. The admin can see a list of Missed jobs with the society, customer, vehicle, crew member, reason, note, photo and date, and can filter it by society, date and reason. | Derived |
| ADM-CNC-03 | Missed is decided for each job. **Cleaning-External:** the next day's regular Cleaning-External job covers it, so there is no extra job and no plan extension and the admin needs to do nothing. The admin can instead mark it skipped by operations, which does not extend the plan (ADM-OPS-03). **Cleaning-Internal and Deep Spa:** the admin either schedules that job again for the next day only, or marks it skipped by operations. A Cleaning-Internal job skipped by operations stays owed in the Interior entitlement and is planned on a later day, with no plan extension (SCHR-INT-21). A skipped Deep Spa is refunded or rebooked by the admin outside the app. A job cannot be scheduled again for any other day, and a job already done is not repeated. A Missed Cleaning-Internal or Deep Spa job with no outcome stays on the Missed list until the admin chooses. A Manager can mark a job skipped in the same way only when `crew.manager_skip` is on (ADM-OPS-04, CRW-MGR-02). The visit is Completed when all its jobs are done or skipped. | Owner, Owner (updated 5 Nov 2026) |
| ADM-CNC-06 | A Cleaning-Internal or Deep Spa job scheduled again is added to the next day's schedule as described in ADM-SCH-26. It is planned like any job of that service, with that service's duration (ADM-SCH-03), and the customer is not charged extra. A job that is deferred because the car or the keys were not available is planned again by the scheduler without this decision (SCHR-DEF-05). The next-day rule applies to the admin's decision after a Missed outcome. | Owner and Derived |
| ADM-CNC-04 | The admin is alerted when a job becomes Missed (ADM-ACC-09). This is one of the admin alerts in ADM-SCH-24. The customer sees "Missed. Rescheduled on dd-Mon-yy" once the admin schedules it again (CAL-09 in the customer file). | Derived and Owner |
| ADM-CNC-05 | The outcome and the admin who chose it are recorded with the time. | Derived |
| ADM-CNC-07 | The remark (free-text note) is mandatory for every **Not Completed** outcome, whoever records it: a crew member, a Manager or the admin. "Not Completed" is the job outcome the crew app calls Could not complete (CRW-CNC-01), also shown to the customer as Missed. The reason stays mandatory too. The reasons stay configured by the admin (ADM-CNC-01). | Owner |
| ADM-CNC-08 | The starting list of reasons (ADM-CNC-01) also holds: different parking location; keys or customer unavailable; access restricted; customer requested no cleaning; weather or operational issue. The admin can rename, reorder and deactivate every reason, these included. | Owner |
| ADM-CNC-09 | When a visit planned as Exterior + Interior has its Exterior job done and its Interior job Not Completed (for example keys or customer unavailable), the visit outcome is **Partially Completed**. The record keeps what was planned and what was delivered, and the admin sees both on the Missed list and on the visit. | Owner |
| ADM-CNC-10 | The admin, or a Manager when the feature flag `crew.manager_reschedule` is on (default on), decides whether to reschedule the missed Interior job of a Partially Completed visit. Until decided, the job stays on the Missed list. Rescheduling a Cleaning-Internal job follows ADM-CNC-03 and ADM-CNC-06: the job is rescheduled for the next day only (owner, 25 Oct 2026). If that day has passed, the admin skips the job instead. This next-day rule stays under the scheduling rules v1.2: only a deferral for an unavailable car or key is planned again automatically (SCHR-DEF-05, owner, 5 Nov 2026). | Owner and Derived |

### 8.3 Feedback, ratings and check-ins

| ID | Requirement | Status |
|---|---|---|
| ADM-FDB-01 | The admin can view customer feedback (category, star rating, comments, date, customer, testimonial permission) and filter it by category, rating, society and date. | Owner |
| ADM-FDB-02 | The admin can view visit ratings with their positive or issue tags and comments, for each visit, and filter them by society and date. Ratings are general and are not tied to a crew member. | Owner |
| ADM-FDB-03 | The admin can see the average rating and how often each tag was selected, by society and period. | Derived |
| ADM-FDB-04 | The admin can view monthly check-in results: the star rating for each category and the comment, by customer, vehicle and renewal cycle, with an average for each category by society. | Owner |
| ADM-FDB-05 | Entries where the customer gave testimonial permission are marked, so Priveo knows which ones it may quote. Entries without permission are never marked usable. | Derived |
| ADM-FDB-06 | The admin can add, rename, edit the description of, and deactivate the **feedback categories**, the **positive rating tags** and the **check-in categories**. The customer app loads these lists from the backend (FDBK-06, SVC-11, CHK-03 in the customer file). | Owner |
| ADM-FDB-07 | A category or tag that is deactivated no longer appears for customers, but feedback already given with it stays and is still readable. | Derived |
| ADM-FDB-08 | At the top of the Feedback tab the admin sees summary tiles: total feedback, the average rating, how many ratings of 5, 4, 3, 2 and 1 stars, and how many customers allow a quote. Choosing a star tile filters the list to that rating. | Owner |

---

## 9. Reference data and settings

| ID | Requirement | Status |
|---|---|---|
| ADM-REF-01 | The admin can add, edit and deactivate **societies**: name, sector, city. The customer's society list shows only active societies. A society with active subscriptions or crew cannot be deactivated (ADM-REF-06). | Owner |
| ADM-REF-02 | The "cars serviced" figure shown in the society list is calculated from the active vehicles in that society. | Derived |
| ADM-REF-03 | The admin can maintain the **vehicle catalogue**: makes, models and variants, and the vehicle category for each. They can add, edit and deactivate them. The customer onboarding dropdowns and the auto-detected category come from it (ONB-09, ONB-11). | Owner |
| ADM-REF-04 | The admin can edit a customer's car details: registration number, make, model, variant and category. Customers cannot change these themselves (VEH-04 in the customer file). | Owner |
| ADM-REF-05 | Removed (owner, 18 Oct 2026): the admin portal no longer shows, uploads or verifies an RC document. The customer app's optional RC upload and status (ONB-12, VEH-03) are not changed by this; the owner has not yet said whether they stay. | Owner |
| ADM-REF-07 | The page for societies, plans, vehicle catalogue, services, checklists, reasons and the add-on catalogue is called **Site Setup**. | Owner |
| ADM-SET-01 | **Plans**: the admin keeps a list of plans and can add, edit and deactivate them. For each plan: the plan name, the monthly price, the struck-through list price, the inclusions shown on the review screen (PAY-01, PAY-02), and whether it includes interior cleaning. The interior care day step in the customer's onboarding appears only when the plan includes interior cleaning (ONB-18). The customer chooses one plan when subscribing and when adding a vehicle (PAY-12). A deactivated plan is no longer offered, and subscriptions already on it continue. Only Premium Care exists to start with. Each plan has a unique, permanent plan ID (PLN-0001, PLN-0002 and so on), shown in the Plans list; new plans get the next number. | Owner |
| ADM-SET-02 | **Payment settings**: the UPI ID and the UPI QR code image shown on the payment screen (PAY-05). | Owner |
| ADM-SET-03 | **Support settings**: the helpline number and the WhatsApp number used by "Call support" and "WhatsApp support", and the support hours shown (SUP-02, SUP-03, SUP-04). | Owner |
| ADM-SET-04 | **Invoice settings**: the seller's legal name, address and GSTIN used on the GST invoices (ADM-PAY-08). The admin edits the three values on the Invoice tab of the Settings page, each saved on its own and recorded in the Audit log (ADM-SET-07). The deploy seeds a value only while it has none, and never replaces one that is there. | Owner (30 Oct 2026) |
| ADM-SET-05 | The Settings page shows each section as its own tab: the setting groups (Support, Payment, Invoice, Schedule, Billing), Alert emails and Automatic planning. The Automatic planning tab holds the planning time only. Switching automatic planning on or off is the switch of the automatic-planning job on the Scheduled jobs page (ADM-OPS-05). | Owner |
| ADM-SET-06 | The Audit trail page does not reload by itself. It tells the admin to press **Refresh** to see newer events. Refresh loads the first page again. It shows 50 events a page, newest first, for the chosen site and All sites (ADM-SET-09), with the range and total ("1-50 of 120"), Previous, Next and the page number. The server pages the list, so there is no limit on how far back the admin can go. | Owner (refresh); Derived (paging) |
| ADM-SET-07 | The Audit trail page also records edits to schedules (including moved services), queue overrides (ADM-SCH-38) and service outcomes (ADM-CNC-05), each with the admin or crew member and the time. It also records every change to a scheduler setting (site or global), a break rule and a cleaner's home zone, reporting time or first-job time, with the admin, the time, the old and the new value and the site (SCHR-CFG-06). | Owner (confirmed 25 Oct 2026), Owner (5 Nov 2026) |
| ADM-SET-08 | A plan can optionally be linked to one vehicle category from the vehicle catalogue (ADM-REF-03). The admin chooses it from a dropdown when adding or editing a plan, can leave it empty, and sees it in the Plans list. In this version the link is only stored and shown: it does not change which plans a customer is offered or what they pay. | Derived |
| ADM-SET-09 | The page called **Audit trail** (before: Audit) is a site page. It follows the master Site selector (ADM-SITE-01) and lists the changes of the chosen site (the society and its zones and working slots, and its customers, vehicles, subscriptions, payments, crew, schedules, jobs, queue overrides and add-on requests) **together with** the changes that belong to no site: Settings, plans, the add-on catalogue, checklists, reasons, feature flags, admin sign-in events such as "log out everywhere", and actions over several sites at once. Those rows show in the Audit trail of every site, and the table has no Site column because the page is already for the chosen site. Nothing is hidden. The filters are From date, To date, Entity and a general **Search**; there is no Actor ID filter. Search is a text box with a **Search** button (Enter does the same) and a **Clear** button. Nothing is sent while the admin types. The button is off until the text has at least 3 characters, and the page says so. A search finds events where the text is part of any column of the table, in any letter case: the date and time (for example 10-Oct-26 or 2026-10-10), the entity (with spaces or underscores), the action, who made the change (the login id), the change (field names and old or new values) and the record id. The search works together with the dates and the entity filter. Refresh works inside this view. Changing the site, a filter or the search returns to the first page. When nothing matches, the page says so. | Owner (5 Nov 2026) |
| ADM-REF-06 | A society can be deactivated only when it has no active subscriptions and no active crew. The admin first deactivates those. Deactivating the society then only removes it from the customer's society list. | Owner |
| ADM-REF-08 | The admin can add, rename, deactivate and reactivate **zones** of a society in Site Setup. A zone name is unique within its society. A deactivated zone is no longer offered in Add Vehicle; vehicles already in it keep it. Each Member or Manager is given one home zone on the crew screen. The scheduler fills a cleaner's home zone first, then uses spare capacity for other zones and records the reason for each cross-zone job. A zone with no cleaner is served as cross-zone work (SCHR-ZONE-01, SCHR-ZONE-03, SCHR-ZONE-06, SCHR-ZONE-07). Changes are recorded in the Audit trail. | Owner and Derived |
| ADM-REF-09 | In Add Vehicle, and when editing a car, the admin can choose one of the society's active zones for the vehicle, or none. The zone is shown with the parking slot wherever the admin and the crew see the slot (ADM-REF-10). The zone is internal: the customer never sees it and cannot set it. Parking text that does not fit a basement and number (for example from a data load) is kept as given until the admin changes it. | Owner and Derived |
| ADM-REF-10 | A vehicle's **zone and parking slot always appear together**: on the vehicle page and its parking panel, on the schedule (board, cards, timeline), and on the crew job card and crew day list, for example "Zone 3 · B2-14". Either part may be missing. The zone is never shown to the customer: the customer app shows the parking slot alone (owner, 3 Nov 2026). A change of a vehicle's zone is written to the audit trail with the old and the new zone name. A change of a customer's alternate names is not audited (ADM-CUS-31). | Owner (3 Nov 2026) |

### 9.1 Service checklists and proof minimums

| ID | Requirement | Status |
|---|---|---|
| ADM-CHK-01 | The admin prepares a checklist for each service (Cleaning-External, Cleaning-Internal, Deep Spa) during app setup. The crew member checks the items of the service they are doing (CRW-SVC-01 to CRW-SVC-03 in the crew file). | Owner |
| ADM-CHK-02 | Only the admin can edit checklists. Crew and customers cannot add, remove or change items. | Owner |
| ADM-CHK-03 | The admin can add, rename, reorder and deactivate the items of each checklist. | Owner and Derived |
| ADM-CHK-04 | The customer sees the checked items, with the time each was checked, in Service Details (SVC-03 in the customer file). | Derived |
| ADM-CHK-05 | An edit applies to visits from then on. A deactivated or renamed item stays readable on visits already done, as it was then (like ADM-FDB-07). | Derived |
| ADM-CHK-06 | For each service the admin sets the minimum number of photos and the minimum number of videos the crew must upload before they can mark a job complete (CRW-SVC-07, CRW-SVC-08). | Owner |
| ADM-CHK-07 | External cleaning retains the prototype list. Use five-step samples for Cleaning-Internal and Deep Spa, editable in the portal and viewable by admin on mobile (owner decision 13 Oct 2026). Issued checklist history remains unchanged. | Owner |

---

### 9.2 Add-ons

| ID | Requirement | Status |
|---|---|---|
| ADM-ADD-01 | The admin keeps a list of add-ons and can add, edit and deactivate them. For each add-on: name, description, price including GST, struck-through list price and duration. Deep Spa (2 hours) is the first. Each add-on has a unique, permanent add-on ID (ADN-0001, ADN-0002 and so on), shown in the Add-on catalogue. The first line of the description is the pitch shown to the customer and every further line is shown as an inclusion. A deactivated add-on is no longer offered, and requests already made continue. | Owner |
| ADM-ADD-02 | The admin can see a list of add-on requests with the customer, vehicle, add-on, proposed date, finish-by time, status (Requested, Scheduled, Completed, Cancelled, Missed), payment status and assigned crew member, and can filter it by status, society, date and add-on. | Derived |
| ADM-ADD-03 | For a request on the Needs scheduling list, the admin agrees a new date with the customer, sets the date and time, and the scheduler then plans it (ADM-SCH-30). The customer sees the assigned crew member and time (CAL-10). | Owner |
| ADM-ADD-04 | The admin can create an add-on request for a customer, for example when the customer asks by phone, and can change or cancel any request at any time. The admin is not bound by the 9 PM deadline (ADM-CUS-11). | Derived |
| ADM-ADD-05 | An add-on's payment appears in the payments list with the type Add-on (ADM-PAY-10). The admin confirms it and can generate its invoice like a plan payment. | Owner |
| ADM-ADD-06 | As an add-on, Deep Spa is bought for a vehicle whose subscription is Active (ADD-01 in the customer file). A customer without a subscription takes it as a standalone service (ADM-ADD-10). | Owner |
| ADM-ADD-07 | A job the crew could not do for an add-on follows the Missed rules (ADM-CNC-03). | Derived |
| ADM-ADD-08 | In MVP scheduling an add-on does not depend on its payment status. This can change later. | Owner |
| ADM-ADD-09 | Every admin action on an add-on request is recorded with the admin and the time. | Derived |
| ADM-ADD-10 | Deep Spa is also a standalone service: a customer who has no subscription can take it (ADD-14 in the customer file). | Owner |
| ADM-ADD-11 | A customer can therefore exist with a vehicle and no subscription. The one-time load of existing customers brings in the people who have taken only a Deep Spa in this way, with their Deep Spa as history. | Derived |
| ADM-ADD-12 | Admin creates a customer/vehicle without a subscription; standalone Spa follows the subscriber Spa booking, UPI, scheduling, proof and history rules. Admin can create its booking too (owner decision 13 Oct 2026). | Owner |
| ADM-ADD-13 | The Add-ons page is called **Add on Service Requests**. | Owner |
| ADM-ADD-14 | Every active add-on in Site Setup is offered to customers, whatever its service, not only Deep Spa (ADD-17). A request records the add-on bought. The admin's Request add-on dialog lets the admin choose the add-on, and the list and booking pages show its name. | Owner (18 Oct 2026) |
| ADM-ADD-15 | The add-on catalogue also includes **Extra interior** and **Special exterior**. Their prices are not decided. The admin cannot activate them for customers until prices are set. | Owner (confirmed 25 Oct 2026) |

### 9.3 Feature flags

| ID | Requirement | Status |
|---|---|---|
| ADM-FLAG-01 | Only the admin can open the **Feature Plugs** page in the portal. It lists the features that can be switched, in tabs for Customers, Crew and Both apps (a tab with no features is hidden). Each tab shows its features in groups, each with a switch and a note on who it affects. Each tab shows how many features it holds and how many are off. | Owner |
| ADM-FLAG-02 | Switching a feature off or on takes effect in the apps without a new build or store release, on Android and iOS alike. | Owner |
| ADM-FLAG-03 | The apps do not poll for flags. They read them once after sign-in or when the app opens signed in, and again only on a hard refresh: pull to refresh, or returning to the app after 5 minutes or more. | Owner |
| ADM-FLAG-04 | Flags add no noticeable delay. The apps keep the last flags on the phone and show screens from them at once. An unchanged answer from the server carries no data. | Owner |
| ADM-FLAG-05 | Turning a feature off asks the admin to confirm. Nothing is deleted: the data stays and the feature returns when switched on. Every change is recorded in the Audit log with the admin and the time. | Derived |
| ADM-FLAG-06 | A feature that is off disappears from the app (buttons, tabs and quick actions) and its page cannot be opened, even from an old link. The server also refuses the request for the main actions of a feature that is off. | Derived |
| ADM-FLAG-07 | If the flags cannot be read, the app keeps the last flags it has, or shows every feature when it has none. A failed read never takes a feature away. | Derived |
| ADM-FLAG-08 | Sign-in, the home screen, the job card flow and payment status handling cannot be switched off. | Derived |

## 10. Business rules

1. The admin sets crew working hours and exceptions, so capacity is always known and accurate.
2. Crew roles are Manager, Member and Trainee. Their privileges are in the crew file. Trainees count as zero capacity, are paired with a Member and get that Member's jobs. Members and Managers count in full.
3. Every crew member and every working slot belongs to one society. Capacity and scheduling are worked out for each society.
4. Each service has one or more independent working slots. The defaults are Cleaning-External and Cleaning-Internal 5 AM to 11 AM every day except the weekly off, and Deep Spa every day except the weekly off at any time of day. All are editable. The weekly-off weekday (Wednesday by default) is left out for all three services, so the site is closed that day (SCHR-PAR-03).
5. Planning durations: Cleaning-External and Cleaning-Internal 30 minutes each, Deep Spa 2 hours. All are editable. The scheduler plans all three.
6. Scheduling only happens when the admin starts it, one period at a time: Daily, Weekly (the default, with the week starting on Sunday) or Monthly. It follows the ordered rules of the scheduler requirements file (SCHR-HIER): Exterior first, then Interior by service week. The service week (Monday to Sunday) is separate from the planning period.
7. A draft can be changed by hand and re-run many times. Re-runs keep the changes made by hand and may suggest improvements. Once frozen it can be changed only after entering the secret code, which is the word "unfreeze".
8. When a schedule is frozen, crew can see their assigned cars. Customers see the assigned crew member and time once the visit is assigned.
9. A customer's skip or pause after a freeze applies automatically, and the admin is notified. A cutoff change after a freeze is a request to the admin, who re-runs the scheduler or changes the schedule by hand, and freezes again.
10. A customer can change their own services and schedule settings. The admin can change them too, and the last change wins.
11. Payment statuses are Not Due, Due, Due today, Over due, Initiated and Paid. The first four follow the cycle dates; the admin approves or rejects an Initiated payment, can record an offline payment, and can set Initiated or Paid. Paid closes the record.
12. Admin actions on payments, complaints and schedules are recorded with who and when.
13. Customers and crew use the mobile app. Admins use the web portal, and a limited set of quick actions in the mobile app. The role on each person's login decides what they see and do.
14. Every admin function is on the web portal. Only the simple quick actions in ADM-ACC-07 are in the mobile app, and that list is expected to shrink.
15. A visit skipped by operations does not extend the plan or change that month's cost (owner decision of 23 Oct 2026, replacing the earlier extension rule). A pause does not move the cycle dates either (owner decision of 4 Nov 2026). A skipped Deep Spa add-on is refunded or rebooked by the admin outside the app.
16. The customer's 9 PM deadline applies to customers only. The admin is not bound by it.
17. A crew member cannot be moved to another society for now.
18. Checklists are set by the admin for each service and only the admin can edit them. The admin also sets the minimum photos and videos for each service.
19. Crew sign in with their mobile number and a generated password that only the admin can reset. A job the crew could not complete is Missed. A Missed Cleaning-External job is covered by the next day's regular job unless the admin skips it by operations. A Missed Cleaning-Internal or Deep Spa job is scheduled again for the next day only, or skipped by operations.
20. A schedule is frozen once, by 8 PM the day before its first day. After a freeze, new visits and redos of Missed jobs are assigned automatically to crew with spare capacity, or go to a Needs scheduling list. Removing work needs no code, adding or moving work does.
21. A billing cycle is 30 calendar days from the first service date. The admin chooses when a subscription becomes Active. An unpaid subscription becomes Inactive after its plan payment has been Over due for 7 days.
22. Sign-in identifiers are unique: a customer's email, a crew member's mobile number and an admin's user ID.
23. The admin can move a payment back to a date-based status, and generate a GST invoice for a Paid payment.
24. Every date shown in the app uses the format dd-Mon-yy, for example 07-Nov-26 (rule 28 in the customer file).
25. Deep Spa is bought separately, as an add-on by a customer with a subscription or as a standalone service by a customer without one. It is planned by the scheduler on the date proposed, and is not dependent on payment status in MVP.
26. Only the admin can skip a visit by operations. A Manager can skip only when `crew.manager_skip` is on (default off). Customer Skip and Pause stay behind `customer.skip_pause`.
27. The remark is mandatory for every Not Completed outcome, and the reasons are configured by the admin. A visit with its Exterior done and its Interior Not Completed is Partially Completed. The admin, or a Manager when `crew.manager_reschedule` is on (default on), decides about rescheduling the missed Interior job.
28. Each crew member has an ordered daily queue. Only the current job can be started. The admin can reorder or unlock with a mandatory reason, an audit entry and a notification to the crew member.
29. The first billing period and plan changes are not prorated. An add-on is charged separately: its payment is Due if not paid by the service date and Over due if the service is completed and the payment is not received.
30. A vehicle's schedule is a Weekly pattern or a Cycle pattern and repeats every billing cycle (ADM-SCH-41).

---

## 11. Data entities implied by the requirements

For your reference when you write the data model. This is a reading of the requirements, not a design.

- **User login**: person, login, role (customer, crew, admin). The role decides which screens the app shows.
- **Admin user**: name, user ID (the first is `priveopapa`), password (stored securely, supplied through `.env` at setup). Created by the initial database seed.
- **Customer login**: as in the customer file: mobile number (login ID), MPIN hash, must change MPIN, email verified, onboarding confirmed. Created when the admin creates the customer.
- **Admin preferences**: scheduling period (Daily, Weekly or Monthly; default Weekly), week start day (Sunday), service week start day (Monday), Interior entitlements for each service week.
- **Cutoff request**: customer's vehicle, old cutoff time, new cutoff time, assigned crew member and time, status (open, handled), handled by and when.
- **Society**: name, sector, city, active flag.
- **Crew member**: name, mobile, society, role (Manager, Member, Trainee), active flag, home zone, reporting time and first-job time (each empty when it follows the site value).
- **Working hours**: crew member, day of week, working or off, start time, end time.
- **Exception**: crew member, type (Sick, Leave, Late start), start date, end date, start time (for Late start).
- **Service**: name (Cleaning-External, Cleaning-Internal, Deep Spa), planned duration (30 minutes for Cleaning-External and Cleaning-Internal, 120 minutes for Deep Spa, all editable).
- **Working slot**: society, service, days of the week, start time, end time. A weekday with no slot is the weekly off.
- **Zone**: society, name, active flag. Each vehicle has one zone and each Member or Manager one home zone.
- **Site scheduling settings**: society, key and value for the reporting time, first-job time, Interior-earliest time, break, cutoff policy and weekend days. A site with no value uses the global default.
- **Break rule**: society, optional crew member, start date, end date, start time, end time, or no break.
- **Interior entitlement**: subscription, service week start, state (Pending, Planned, Completed, Waived, Cancelled), job, completed on, waived reason.
- **Cross-zone reason and run configuration snapshot**: on a job, the reason it was given to a cleaner outside the home zone. On a scheduler run, the values it used (SCHR-ZONE-06, SCHR-CFG-08).
- **Capacity**: calculated per society and date, not stored by hand.
- **Schedule**: society, date range, status (Draft, Frozen), frozen by and when, unfrozen by and when.
- **Scheduled visit**: schedule, customer's vehicle, service, date, crew member, start and end time, entered by hand (yes or no), status (scheduled, unscheduled and why, or skipped by operations with a reason).
- **Scheduler suggestion**: schedule, proposed change, applied or ignored.
- **Secret code**: the word "unfreeze", checked by the backend.
- **Audit entry**: admin, action, target, time.
- **Payment**: as in the customer file, with the admin who last changed the status.
- **Complaint**: as in the customer file, with status changes and update notes, each with admin and time.
- **Feedback category, positive rating tag, check-in category**: name, description, active flag.
- **Vehicle catalogue**: make, model, variant, vehicle category, active flag.
- **Crew login**: as in the crew file. The admin generates and resets the password and sees whether the login is blocked after wrong attempts.
- **Session**: login (customer, crew or admin), device name, platform, app version, signed-in time, last-active time, ended time and reason (log out, password reset, deactivation, admin sign-out, inactivity). Used for session management by the admin and for "Sign out of all devices".
- **Checklist**: service, ordered items (name, active flag), minimum photos, minimum videos.
- **Could-not-complete reason**: name, active flag.
- **Could-not-complete record**: as in the crew file, with the admin outcome, handled by and when. The remark is mandatory.
- **Feature flag**: key (`customer.skip_pause`, `crew.manager_skip`, `crew.manager_reschedule`), on or off. Defaults: skip_pause as today, manager_skip off, manager_reschedule on.
- **Schedule pattern**: vehicle, type (Weekly, Cycle), Exterior weekdays and Interior weekdays (Weekly), or day numbers with counts of Exterior-only and Exterior + Interior days (Cycle). It repeats every billing cycle.
- **Queue entry and override**: crew member, date, position, locked or unlocked, and for each override the admin, the reason and the time.
- **Visit outcome record**: planned services and delivered services, original date and revised date (when moved), state (Scheduled, Completed, Partially Completed, Not Completed, Rescheduled, Cancelled).
- **Parking change**: vehicle, new location, start date, end date (empty for a permanent change).
- **Plan history**: subscription, plan, effective date, changed by.
- **Plan**: name, monthly price, list price, inclusions, active flag. Several plans can exist.
- **Invoice**: payment, invoice number, date, amount and GST breakdown, seller details, generated by and when.
- **Invoice settings**: seller legal name, address, GSTIN, invoice number format.
- **Needs scheduling entry**: visit, reason (late visit, crew removed, nobody fits), time added, handled by and when.
- **Add-on / Add-on request**: as in the customer file. A request is planned as a scheduled job and has its own payment of type Add-on. The customer may have no subscription (standalone Deep Spa).
- **Payment settings**: UPI ID, UPI QR code image.
- **Support settings**: helpline number, WhatsApp number, support hours.

---

## 12. Customer requirements and the admin features that cover them

| Needed by (customer file) | Admin capability | Covered by |
|---|---|---|
| PAY-08, PAY-09: payment confirmed by the admin | Update payment status | ADM-PAY |
| ONB-16, CAL-10: slot assigned by the admin | Scheduling and freeze. Crew see the assignment on freeze, and customers see the assigned crew member and time once assigned. | ADM-SCH |
| SCHED-02: customers call the helpline for changes after 9 PM | Admin changes after the customer's deadline | ADM-CUS-09, ADM-CUS-11 |
| FDBK-06, SVC-11, CHK-03: categories and tags configurable by the admin | Add, edit and deactivate them | ADM-FDB-06 |
| CMP-02, CMP-04: complaint status and notes drive the customer's push notification | Manage complaints | ADM-CMP |
| NOTIF-04: "service skipped" also fires when crew or operations skip a visit | Mark a visit as skipped by operations | ADM-OPS |
| FDBK-03, SVC-12, CHK-04: feedback, ratings, tags and check-ins go to the Priveo team | View feedback, ratings and check-ins | ADM-FDB |
| ONB-03: list of societies with cars serviced | Manage societies | ADM-REF-01, ADM-REF-02 |
| ONB-09, ONB-11: make, model, variant and vehicle category lists | Manage the vehicle catalogue | ADM-REF-03 |
| VEH-03, VEH-04: RC status; car details change only through support | Edit car details, verify the RC | ADM-REF-04, ADM-REF-05 |
| PAY-01, PAY-02, PAY-05, SUP-02, SUP-03, SUP-04: plan price and inclusions, UPI QR code and ID, helpline and WhatsApp numbers | Maintain these settings | ADM-SET |
| SVC-03: checklist items with completion times | Maintain checklists for each service | ADM-CHK-01 to ADM-CHK-05 |
| Crew file: minimum photos and videos before "Mark complete" | Set the minimums for each service | ADM-CHK-06 |
| Crew file: Could not complete reasons and Missed visits | Manage the reasons and decide the outcome | ADM-CNC |
| Crew file: login details and password reset | Generate and reset crew passwords and show them once to the admin | ADM-CRW-17, ADM-CRW-18 |
| AUTH-14, ONB-25: customers sign in only if the admin created them, then review the details | Create customers, send the welcome email, manage sign-in | ADM-CUS-01, ADM-CUS-04, ADM-CUS-17 to ADM-CUS-21 |
| ADD-01 to ADD-15: Deep Spa as an add-on and as a standalone service | Manage add-ons and requests | ADM-ADD, ADM-SCH-30, ADM-SCH-31 |
| SUB-05, SUB-11: subscription states and Inactive | Start, stop and reactivate subscriptions | ADM-SUB |
| Crew file: ordered daily queue, unlocking and Partially Completed | Reorder or unlock the queue and decide on a missed Interior job | ADM-SCH-38, ADM-CNC-09, ADM-CNC-10 |
| ADD-18: add-on payment becomes Due or Over due | Payment rules for add-ons | ADM-PAY-13 |
| HIST-04, CAL-11: service history and day states | Service history for a vehicle | ADM-CUS-29 |
| SKIP-10: customer Skip and Pause behind a flag | Feature flags | ADM-OPS-04 |
| ONB-18, SUB-08: the interior care day is a preference, not a promise | Interior entitlement for each service week, planned on any working day | ADM-SVS-10, SCHR-INT-05, SCHR-INT-06 |
| ONB-16, SCHED-01: the cutoff the customer chooses | Customer cutoff policy: hard on weekdays, flexible on the weekend | ADM-SCH-07, SCHR-CUT, SCHR-WKE |
| PAY-02: plan inclusions no longer say 7 days a week | Weekly off weekday set in the working slots | ADM-SVS-05, SCHR-PAR-03 |

---

## 13. Open questions

Open from the crew work and the review:

Resolved 13 Oct 2026: use editable five-step samples for ADM-CHK-07, with mobile read access.
Resolved 13 Oct 2026: standalone Spa uses the same rules as subscriber add-on Spa; see [the owner decisions](owner-decisions-2026-10-13.md).
Resolved 23 Oct 2026: see [the owner decisions](owner-decisions-2026-10-23.md). A skip no longer extends the plan; the remark is mandatory for every Not Completed outcome; no proration; add-on payment rule; crew queue; Partially Completed.

Open from the 23 Oct 2026 review:

1. The prices of Extra interior and Special exterior (ADM-ADD-15). Answered 25 Oct 2026: the admin sets add-on prices in the catalogue.
2. Whether the customer can choose a Weekly or Cycle pattern in their own app (ADM-SCH-41). Answered 25 Oct 2026: only the admin. The customer keeps the single interior care day (ONB-18).
3. A plan change from a chosen date (ADM-SUB-08): the owner answered on 25 Oct 2026 that the admin decides the charge for the days before the renewal for each customer. Answered.
4. A missed Interior job of a Partially Completed visit is rescheduled for the next day only (ADM-CNC-10): answered 25 Oct 2026. The customer is notified of a Partially Completed visit (CAL-11): answered 25 Oct 2026.
5. ADM-SCH-37, ADM-SCH-39, ADM-SCH-40, ADM-CUS-27, ADM-CUS-29, ADM-SUB-08, ADM-ACC-16 and ADM-SET-07 were confirmed by the owner on 25 Oct 2026. Answered.

Resolved 5 Nov 2026: the 16 scheduling-rules questions are answered in section 13 of `scheduler-requirements.md`. They change the weekly off, the Interior entitlement and carry-forward, the service week, durations, the break, the cutoff policy, zones, Custom interior day (ADM-SUB-10), hand placement and deferral.

Answered during the review: Deep Spa is bought separately, as an add-on by subscribers and as a standalone service by others (revised 10 Oct 2026), and is separate from the day's plan visit; the customer proposes one date and a finish-by time; scheduling does not wait for payment; the customer can change or cancel until 9 PM the day before; a job that cannot fit goes to the admin's list; the plan is chosen before service preferences when a customer adds a vehicle; a Trainee has no jobs when the paired Member is absent; sign-in limits are as written in AUTH-05 to AUTH-13; the customer can change names, mobile number, parking, vehicle photo, cutoff time and interior day in the onboarding review; the first payment is asked only if Due or Over due; ratings are general; one crew card for each job; a skipped interior day is lost for that week; Deep Spa is 2 hours and Internal is 20 minutes; a plan change starts at the next renewal; Missed shows "Missed. Rescheduled on dd-Mon-yy"; crew roles and privileges.

---

## 14. Deferred to V2 and out of scope

### Deferred to V2

| Area | Item |
|---|---|
| Crew | Moving a crew member to another society |
| Security | Two-factor sign-in for admins; an IP allowlist or AWS WAF rules in front of the web portal |

### To be specified later by the owner

- Starting checklists were resolved on 13 Oct 2026 (ADM-CHK-07).
- Standalone Spa flow was resolved on 13 Oct 2026 (ADM-ADD-12).

### Out of scope for this file

- Crew app features (Part 3), which are in `crew-functional-requirements.md`.

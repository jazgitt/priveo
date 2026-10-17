# Priveo Car Concierge: Admin Functional Requirements

**Status:** Draft v0.13 (crew society moves from a date; plan and add-on IDs; complaint 4-hour target is internal only; welcome email not resendable, 16 Oct 2026): owner decisions of 9 Oct 2026; crew-driven additions; email sign-in for customers; Deep Spa is an add-on for subscribers and a standalone service for others (owner decision of 10 Oct 2026); admin web portal in MVP with a limited set of mobile quick actions; consistency pass
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
| ADM-ACC-06 | An admin signs in to the web portal with the same user ID and password as in the app (ADM-ACC-05). The wrong-password lock applies (CRW-ACC-07 in the crew file). | Owner and Derived |
| ADM-ACC-07 | The mobile app gives the admin a limited set of **quick actions**: (a) phone push alerts (ADM-ACC-09); (b) confirm or reject a payment, that is, set its status (ADM-PAY-02); (c) see the Needs scheduling list and the day's schedule, read-only; (d) mark a visit skipped by operations, and choose the outcome of a Missed job (ADM-OPS-01, ADM-CNC-03); (e) skip, un-skip, pause and end a pause for a customer's vehicle, on behalf of the customer (ADM-CUS-09); (f) other simple actions that are not complex transactions: search and view customers, view and update complaints (status and notes), view feedback, ratings and check-in results, view capacity, view the crew list and add crew exceptions, and view add-on requests. | Owner |
| ADM-ACC-08 | Everything else is **web portal only**: creating and editing customers, vehicles, subscriptions and schedule settings (the plan, service cutoff time and interior care day; skip, un-skip and pause are also on mobile, ADM-ACC-07); creating add-on requests; onboarding crew, roles, Trainee pairing, working hours, deactivation, password resets and crew and customer session management (ADM-CRW-21, ADM-CUS-21); services and working slots; running, reviewing, editing, freezing and unfreezing the scheduler; preferences; reference data and settings (societies, vehicle catalogue, plans, add-ons, checklists, reason lists, feedback and check-in categories, payment, support and invoice settings); GST invoice generation; and audit views. | Owner |
| ADM-ACC-09 | Admin alerts (ADM-SCH-24) reach the admin in three ways: a phone push in the mobile app, a notification bell with an unread count in the web portal, and an email for each alert. The admin can switch the emails off. The bell and the phone push cannot be switched off. | Owner |
| ADM-ACC-10 | The web portal and the mobile app use the same backend and the same rules. A change made in one shows in the other at once, and the last change wins, as in ADM-CUS-10. | Derived |
| ADM-ACC-11 | The list of mobile quick actions is expected to shrink. Actions that turn out to be complex for a phone are removed from the mobile app and stay on the web portal. | Owner |
| ADM-ACC-12 | The web portal keeps the admin signed in with an HttpOnly, secure cookie, not with tokens in browser storage, and every change request carries CSRF protection. A web session ends after 60 minutes of inactivity, and the admin signs in again. | Owner |
| ADM-ACC-13 | In the mobile app an admin stays signed in until they log out, their password is changed, or they have not used the app for 24 hours, and then they sign in again. The 60-minute inactivity time-out applies only to the web portal (ADM-ACC-12). Because the admin password is set at seed time, a lost admin phone is also handled by "Sign out of all devices" (ADM-ACC-14). | Owner |
| ADM-ACC-14 | The admin has a **Sign out of all devices** action, on the web portal and in the mobile app. It ends every session of the admin's own login, on the web and on phones, at once, including the one in use. The admin then signs in again where needed. The action is recorded with the time. | Owner |

---

## 2. Customers

### 2.1 Onboard a customer manually (item a)

| ID | Requirement | Status |
|---|---|---|
| ADM-CUS-01 | The admin can create a customer on the customer's behalf. The form follows the customer's own onboarding: first name, last name, email (required), mobile number (required contact number); society; vehicle (make, model, variant, registration number, optional RC document); parking (basement, number); plan; service cutoff time; interior care day (only when the plan includes it). | Owner |
| ADM-CUS-02 | The same validation as customer onboarding applies: valid email address, 10-digit mobile number, registration number format, required fields. | Derived |
| ADM-CUS-03 | An email can belong to only one customer. If it already exists, the app opens that customer instead of creating a duplicate. The mobile number is a contact detail and is not checked for duplicates. | Derived and Owner |
| ADM-CUS-04 | After the admin creates the customer, a welcome email is sent to the customer's email. It says the account is ready and asks them to open the app and sign in with that email. It contains no code or password. The customer then enters their email in the app, gets a 6-digit verification code, sets a password and reviews the details the admin entered (AUTH-14, ONB-25 in the customer file). No SMS is sent. | Owner |
| ADM-CUS-05 | The admin can add further vehicles to an existing customer. Each vehicle has its own subscription. | Derived |
| ADM-CUS-06 | The admin can set the first payment's status when onboarding (see section 6). | Owner |
| ADM-CUS-07 | The vehicle photo is mandatory. When the admin onboards a customer, the admin can upload it. The customer can replace it later in their own app. | Owner |

### 2.2 Find and view customers

| ID | Requirement | Status |
|---|---|---|
| ADM-CUS-08 | The admin can search the customer list by name, mobile number, registration number or society, and open a customer to see their vehicles, subscriptions, schedule settings and payment statuses. | Derived |
| ADM-CUS-17 | In the customer view the admin sees whether the customer has verified their email, set a password and confirmed the onboarding review. | Derived |
| ADM-CUS-18 | Removed (owner, 16 Oct 2026): the admin cannot resend the welcome email. The welcome email is sent once, when the customer is created (ADM-CUS-04) or the email is corrected (ADM-CUS-19). | Owner |
| ADM-CUS-19 | The admin can correct a customer's email. The customer's password is cleared, a new welcome email is sent, and the customer verifies the new email and sets a new password. The change is audited (ADM-CUS-16). | Owner |
| ADM-CUS-20 | The admin can reset a customer's password by clearing it. The customer then gets an emailed code at the next sign-in, as for a first sign-in. The change is audited (ADM-CUS-16). | Derived |
| ADM-CUS-21 | The admin can manage a customer's signed-in sessions. The admin sees each active session with its device name, platform, app version and last-active time, and can sign out one session or all of the customer's sessions. The customer is signed out at once and sees the sign-in screen the next time the app contacts the server. Each sign-out is recorded with the admin and the time (ADM-CUS-16). Changing a customer's email or clearing their password (ADM-CUS-19, ADM-CUS-20) also ends all their sessions. | Owner |

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

---

### 2.5 Subscription start and status

| ID | Requirement | Status |
|---|---|---|
| ADM-SUB-01 | A new subscription starts as **Activating**. The admin chooses when it becomes **Active** and sets its first service date, whatever the payment status. The billing cycle starts on that first service date (rule 26 in the customer file). Visits are scheduled only for Active subscriptions. | Owner |
| ADM-SUB-02 | The admin can set a vehicle's subscription to **Inactive**, with a reason. Its future visits are removed from schedules (without the code, ADM-SCH-29), and the vehicle no longer counts in capacity demand (ADM-CAP-03) or in "cars serviced" (ADM-REF-02). The customer sees Inactive. | Owner and Derived |
| ADM-SUB-03 | The backend sets a subscription to Inactive automatically when its plan payment has been **Over due for 7 days**. An Over due add-on payment does not do this. The admin is alerted (ADM-SCH-24). The admin can override it. | Owner |
| ADM-SUB-04 | The admin can reactivate an Inactive subscription: it returns to Activating, and the admin then sets the first service date and activates it as in ADM-SUB-01. A new billing cycle and a new Due payment start from that date. Renewal by the customer is V2. | Derived |
| ADM-SUB-05 | Every change of subscription status is recorded with the admin, or the backend, and the time. | Derived |

## 3. Crew

### 3.1 Onboard crew (items b, c, e)

| ID | Requirement | Status |
|---|---|---|
| ADM-CRW-01 | The admin can onboard one or more crew members. Several can be added in one session, one after another, without leaving the screen. | Owner (item b) |
| ADM-CRW-02 | Details for each crew member: name, mobile number, society, role (Manager, Member or Trainee, required) and working hours. | Owner |
| ADM-CRW-03 | The admin can change a crew member's role at any time, including assigning the Manager role to a crew member. | Owner (item c) |
| ADM-CRW-16 | One or more crew members can be given the Manager role, when they are onboarded or later. A society can have several Managers. | Owner |
| ADM-CRW-17 | Onboarding a crew member creates their login with the Crew role, so they can use the app as soon as they are onboarded. The login ID is the crew member's mobile number. A password is generated automatically (the first 3 letters of the name, 4 random digits and `$`). Passwords are never sent by SMS or WhatsApp: the app shows the login ID and the password to the admin once, with a Copy button, and the admin gives them to the crew member outside the app (CRW-ACC-05 in the crew file). | Owner |
| ADM-CRW-18 | The admin can reset a crew member's password. A new password is generated in the same format and shown to the admin once, as at onboarding (ADM-CRW-17). The old password stops working at once. Crew cannot change their own password or login ID (CRW-ACC-06 in the crew file). The admin can also unlock a crew login that was locked after wrong attempts. | Derived |
| ADM-CRW-04 | Working hours are set during onboarding for every crew member, whatever their role. For each day of the week the admin marks the day as working or off and sets a start time and an end time. | Owner (item e) |
| ADM-CRW-05 | The admin, and a Manager for crew in their society (CRW-MGR-05), can edit working hours later. The change applies to dates from then on. | Derived |
| ADM-CRW-06 | A mobile number can belong to only one crew member, because it is their login ID. | Derived |
| ADM-CRW-07 | The admin can see the crew list with each person's society, role, working hours and upcoming exceptions, and can search and filter it by society. | Derived |
| ADM-CRW-13 | Every crew member belongs to exactly one society at a time. The admin can move a crew member to another society (ADM-CRW-22). | Owner (18 Oct 2026) |
| ADM-CRW-14 | Trainees count as zero capacity. They appear in the crew list but add nothing to capacity, and the scheduler does not assign visits to them directly. A Trainee gets the jobs of the Member they are paired with (ADM-CRW-19). | Owner |
| ADM-CRW-19 | Every Trainee is paired with a Member of the same society. The admin chooses the Member when onboarding the Trainee and can change it later. A Member can have more than one Trainee, and a Trainee has exactly one Member. Changing a Trainee's role to Member, or a Member's role while Trainees are paired with them, requires pairing to be fixed first. | Owner and Derived |
| ADM-CRW-20 | A Manager can also perform the actions in section 3a of the crew file for crew in their society: see the society's schedule, mark a job Could not complete or skipped, reassign a job, add exceptions, and edit crew working hours. These are recorded with the Manager's name and the time, like admin actions (ADM-SCH-19). | Owner |
| ADM-CRW-21 | The admin can manage a crew member's signed-in sessions. For a crew member the admin sees each active session with its device name, platform, app version and last-active time. The admin can sign out one session or all of that crew member's sessions. The crew member is signed out at once and sees the sign-in screen the next time the app contacts the server. Sessions also end when the crew member is deactivated or their password is reset (CRW-ACC-11). Each sign-out is recorded with the admin and the time. | Owner |
| ADM-CRW-22 | The admin can change a crew member's society from a date the admin picks, which is today or a later day. The society is a dated record: each stay in a society is kept with its start date and ends the day before the next one starts. Earlier stays are never changed and a past date cannot be chosen. The crew member's details page shows the history of stays. A move that has not started yet can be cancelled, and only one move can be waiting at a time. | Owner (18 Oct 2026) |
| ADM-CRW-23 | When a move takes effect, the crew member's open jobs from that day on in the old society go back to the Needs scheduling list (ADM-CRW-12); started and finished jobs and earlier dates stay as they were. From then on the scheduler counts the crew member in the new society. A Trainee being moved is given a Member of the new society to pair with. A Member whose Trainees are still paired with them cannot be moved until the Trainees are paired with another Member. A Member who has a move waiting cannot be chosen as a Trainee's Member. | Derived |
| ADM-CRW-15 | The admin can deactivate a crew member who has left. A deactivated crew member no longer counts in capacity or the scheduler, and cannot sign in. Their past visits and records stay. | Derived (in MVP) |

### 3.2 Exceptions (item f)

| ID | Requirement | Status |
|---|---|---|
| ADM-CRW-08 | The admin can mark an exception for a crew member on one date or a date range. Types: **Sick**, **Leave**, **Late start**. | Owner (item f) |
| ADM-CRW-09 | Sick and Leave remove the crew member from the whole day. Late start removes the crew member until the start time the admin enters for that day. | Derived |
| ADM-CRW-10 | The admin can edit or remove an exception. | Derived |
| ADM-CRW-11 | Capacity is recalculated as soon as an exception is saved, edited or removed, so it is always accurate (section 5). | Owner |
| ADM-CRW-12 | If an exception affects visits that are already scheduled, the app lists the affected visits so the admin can reassign them. On a frozen schedule the exception removes the crew member's visits without the code (ADM-SCH-29). The visits then go to the Needs scheduling list (ADM-SCH-28), and reassigning them needs the code (ADM-SCH-17) or happens automatically if a crew member fits (ADM-SCH-27). | Derived |

---

## 4. Services and working slots (item d)

| ID | Requirement | Status |
|---|---|---|
| ADM-SVS-01 | There are three services: **Cleaning-External**, **Cleaning-Internal** and **Deep Spa**. In the customer app Cleaning-External and Cleaning-Internal appear as the visit types Exterior and Exterior + Interior, and Deep Spa appears as the Full spa add-on. Every visit includes one Cleaning-External. The interior care day adds Cleaning-Internal. Deep Spa is not part of the plan: it is an add-on that existing customers buy separately (section 9a of the customer file, ADM-ADD). If the interior care day is skipped, paused or skipped by operations, that week's Cleaning-Internal is lost and not made up. Each service is a **separate job**, with its own job card, checklist, proof and completion (CRW-SCH-05 in the crew file). The customer's visit is Completed when all of its jobs are done. | Owner |
| ADM-SVS-02 | A working slot is a start time and an end time on chosen days of the week, during which that service can be done. Every working slot belongs to one society. | Owner |
| ADM-SVS-03 | A service can have several independent working slots in a society, for example 5 to 8 AM and 4 to 6 PM. | Owner |
| ADM-SVS-04 | The admin can add, edit and delete working slots for every service, for each society. | Owner |
| ADM-SVS-05 | Default working slots: **Cleaning-External**: 5 AM to 11 AM, every day of the week. **Cleaning-Internal**: 5 AM to 11 AM, every day of the week. **Deep Spa**: every day of the week, at any time of day. Every day is open: there is no rest day. | Owner |
| ADM-SVS-06 | A new society starts with the default working slots, which the admin can then edit. | Derived |
| ADM-SVS-07 | A slot's end time must be after its start time, and two slots of the same service cannot overlap on the same day in the same society. | Derived |
| ADM-SVS-08 | Changes to working slots apply to scheduling from then on. A frozen schedule is not changed by them. | Derived |
| ADM-SVS-09 | Planning durations: **Cleaning-External** about 20 minutes (one crew member does 3 in 1 hour), **Cleaning-Internal** about 20 minutes, and **Deep Spa** 2 hours (120 minutes). These apply to every vehicle category for now. | Owner |
| ADM-SVS-10 | The scheduler plans all three services with these durations (ADM-SVS-09), each as its own job. Cleaning-External is due every day and Cleaning-Internal on the customer's interior care day. A Deep Spa job is planned when a customer buys it, as an add-on or as a standalone service (ADM-ADD-10), on the date and finish-by time proposed (ADM-SCH-30). | Owner |

---

## 5. Capacity

Capacity is worked out for each society, because crew and working slots belong to one society each.

| ID | Requirement | Status |
|---|---|---|
| ADM-CAP-01 | The admin can see the capacity for each society and date: the crew hours available that day, from every counted crew member's working hours minus their exceptions, and what fits in it, counted in minutes: 20 for each Cleaning-External or Cleaning-Internal and 120 for each Deep Spa (ADM-SVS-09). | Owner (items e, f) |
| ADM-CAP-02 | Trainees add zero (ADM-CRW-14). Members and Managers both count in full. | Owner |
| ADM-CAP-03 | Next to capacity the admin sees the demand for that date in the same minutes: one Cleaning-External for each active vehicle (after skips and pauses), plus the Cleaning-Internal and Deep Spa jobs due that day, and how many of them have been scheduled so far. | Derived |
| ADM-CAP-04 | Dates where demand is higher than capacity are marked, so the admin can act before scheduling. | Derived |
| ADM-CAP-05 | The capacity figure is always current. It updates immediately when crew are added or deactivated, working hours change, or an exception is saved. | Owner |

---

## 6. Payments (item h)

| ID | Requirement | Status |
|---|---|---|
| ADM-PAY-01 | The admin can see a list of payments and filter by status (Due, Over due, Initiated, Received), customer, vehicle and due date. | Derived |
| ADM-PAY-02 | The admin can update the status of any payment to **Due**, **Over due**, **Initiated** or **Received**. | Owner (item h) |
| ADM-PAY-03 | When the admin sets a payment to **Received**, the payment record is closed and the customer sees Received (PAY-08, PAY-09 in the customer file). | Owner |
| ADM-PAY-04 | The admin can record a payment for a customer who paid offline or in person, without the customer marking it Initiated first. | Derived |
| ADM-PAY-05 | Every status change records which admin made it and when. | Derived |
| ADM-PAY-06 | The backend creates each plan payment 7 days before the renewal date, as Due by the renewal date, and moves it to Over due when the due date passes unpaid. If a pause or a skip by operations moves the renewal date before the payment is Received, the due date moves with it. An add-on payment is created Due on the day the add-on is requested and moves to Over due the next day if unpaid. The admin can override. | Owner and Derived |
| ADM-PAY-07 | The admin can move a payment back from Initiated or Received to Due or Over due, for example when the customer marked it paid but the money did not arrive, or Received was set by mistake. The renewal reminders then resume (NOTIF-05 in the customer file). The customer is not sent a new notification and sees the new status in the app. The change is audited (ADM-PAY-05). | Owner and Derived |
| ADM-PAY-08 | When a payment is **Received**, the admin can generate a GST invoice for it. The customer can view it in billing history (SUB-06 in the customer file). The invoice fields come from the invoice settings (ADM-SET-04). | Owner |
| ADM-PAY-09 | The invoice number is **PRV** + the month + the year as two digits (YY) + the last 4 digits of the customer's mobile number + 4 random digits. The month is two digits (01 to 12). Example for October 2026, mobile ending 4321: `PRV10264321` followed by 4 random digits such as `8052`. The backend generates it and makes sure it is unique, drawing new random digits if the number already exists. | Owner |
| ADM-PAY-10 | Every payment has a type: **Plan** or **Add-on**. The payment list can be filtered by type, and the status rules, audit and GST invoice (ADM-PAY-02 to ADM-PAY-08) work the same for both. | Derived |
| ADM-PAY-11 | When a customer marks a plan or add-on payment as paid and its status becomes Initiated, the admin is alerted (ADM-ACC-09). | Owner |

---

## 7. Scheduling (items j, k)

Scheduling turns the customers' services and the crew's capacity into a plan of who does which visit, and when.

### 7.1 Run the scheduler (item j)

| ID | Requirement | Status |
|---|---|---|
| ADM-SCH-01 | The admin starts scheduling for a chosen society, or all societies, and a date range. Nothing is scheduled until the admin starts it. | Owner (item j) |
| ADM-SCH-02 | For each society the scheduler uses only that society's crew, working slots and customers. | Owner |
| ADM-SCH-03 | The scheduler plans all three services, each as its own job with its own duration (ADM-SVS-09, ADM-SVS-10). | Owner |
| ADM-SCH-04 | The scheduler uses: each customer's schedule settings (cutoff time, interior care day, skips, pauses), add-on requests, the working slots of each service, every counted crew member's working hours, and crew exceptions. Trainees are never assigned directly: they get the jobs of their paired Member (ADM-CRW-19). | Owner and Derived |
| ADM-SCH-05 | The goal of the scheduler is to make the greatest use of the crew's capacity. | Owner |
| ADM-SCH-06 | The result is a draft schedule: for each visit, the date, the crew member and a time inside a working slot. | Derived |
| ADM-SCH-07 | A visit should finish by the customer's service cutoff time. The customer can choose any cutoff time (ONB-16), so the scheduler does not assume it can be met: a visit that cannot be placed without breaking it is flagged for the admin. | Owner |
| ADM-SCH-08 | Visits that cannot be placed, for example because capacity is short, are listed as **Unscheduled** with the reason. | Derived |
| ADM-SCH-09 | One scheduler run covers one period. The period is a week by default, and the week starts on Sunday. The admin can switch it to Daily or Monthly in Preferences (ADM-PRF-01). | Owner |
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
| ADM-SCH-26 | A job scheduled again after a Missed outcome (ADM-CNC-06) goes into the next day's schedule. If that schedule is frozen, it is assigned automatically as in ADM-SCH-27, with no code, or goes to the Needs scheduling list if no crew member fits (ADM-SCH-28). If that schedule is still a draft, it is placed with the other jobs. | Owner |
| ADM-SCH-27 | After a schedule is frozen, a visit that needs a crew member (a new customer or vehicle, an un-skip, an ended pause, or a reactivated subscription) is **assigned automatically** without unfreezing. The system picks a counted crew member of the same society who has spare capacity, the visit's slot allows it and no other job overlaps, and gives the earliest time before the customer's cutoff time. The admin is alerted (ADM-ACC-09) and the crew member gets a push notification. | Owner |
| ADM-SCH-28 | If no crew member fits, the visit goes to a **Needs scheduling** list and the admin is alerted (ADM-ACC-09). The admin then adds it by hand (ADM-SCH-13 and ADM-SCH-17) or re-runs the scheduler. | Derived |
| ADM-SCH-29 | **Removing** work from a frozen schedule does not need the secret code: a visit skipped by operations, a crew exception, a crew deactivation, or a visit removed by the customer's skip or pause. The visits left without a crew member go to the Needs scheduling list (ADM-SCH-28). Adding or moving work by hand needs the code. | Owner and Derived |
| ADM-SCH-30 | An add-on request (Deep Spa) is planned as a job of its own duration on the date the customer proposed, with the customer's finish-by time, in the same way as other jobs (ADM-SCH-03). It does not wait for payment (ADM-ADD-08). If it cannot be placed it goes to the Needs scheduling list (ADM-SCH-28). | Owner |
| ADM-SCH-31 | If a customer cancels an add-on after the schedule is frozen, the job is removed from the schedule automatically, without unfreezing, and the admin is notified (like ADM-SCH-21). If the customer changes the date or finish-by time after the freeze, the change is saved as a request to the admin (like ADM-SCH-22). The admin deals with it as in ADM-SCH-23. | Owner and Derived |

### 7.3 Preferences

| ID | Requirement | Status |
|---|---|---|
| ADM-PRF-01 | The admin has a Preferences screen. It holds the scheduling period, with three options: **Daily**, **Weekly** and **Monthly**. The default is Weekly, with the week starting on Sunday. Monthly covers one calendar month. | Owner |

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
| ADM-CMP-08 | The admin is alerted when a customer raises a complaint (ADM-ACC-09), and again when a complaint is still Raised after 4 hours (ADM-CMP-06). The alert email gives the customer's first name, the category, the visit date if one is linked, the start of the description, and a link that opens the complaint in the web portal. Photos are not attached; the admin sees them in the portal. | Owner |

### 8.2 Visits skipped by operations

| ID | Requirement | Status |
|---|---|---|
| ADM-OPS-01 | The admin can mark a scheduled visit or job as skipped by operations, for example when crew are unavailable. The visit shows as Skipped for the customer, who gets a "Service skipped" push notification if they have it switched on (NOTIF-04 in the customer file). | Owner |
| ADM-OPS-02 | The admin can add a reason when skipping a visit. | Derived |
| ADM-OPS-03 | A Cleaning-External visit skipped by operations is added to the end of the plan. For each day skipped, the plan is extended by one day, so the renewal date moves forward by one day and the customer is not charged extra. A skipped Cleaning-Internal job is lost for that week and does not extend the plan. A skipped Deep Spa add-on does not extend the plan, and any refund or rebooking is handled by the admin outside the app. | Owner |

### 8.2a Visits the crew could not complete

| ID | Requirement | Status |
|---|---|---|
| ADM-CNC-01 | The admin can add, rename, reorder and deactivate the **could-not-complete reasons** the crew choose from (for example car not in the parking spot, car locked, customer did not allow, bad weather, other). A deactivated reason no longer appears for crew, and past records keep it. | Derived |
| ADM-CNC-02 | When a crew member marks a job Could not complete (CRW-CNC-01), the job is **Missed**. The admin can see a list of Missed jobs with the society, customer, vehicle, crew member, reason, note, photo and date, and can filter it by society, date and reason. | Derived |
| ADM-CNC-03 | Missed is decided for each job. **Cleaning-External:** the next day's regular Cleaning-External job covers it, so there is no extra job and no plan extension and the admin needs to do nothing. The admin can instead mark it skipped by operations, which extends the plan by one day (ADM-OPS-03). **Cleaning-Internal and Deep Spa:** the admin either schedules that job again for the next day only, or marks it skipped by operations. A skipped Cleaning-Internal job is lost for that week with no plan extension, and a skipped Deep Spa is refunded or rebooked by the admin outside the app. A job cannot be scheduled again for any other day, and a job already done is not repeated. A Missed Cleaning-Internal or Deep Spa job with no outcome stays on the Missed list until the admin chooses. A Manager can mark a job skipped in the same way (CRW-MGR-02). The visit is Completed when all its jobs are done or skipped. | Owner |
| ADM-CNC-06 | A Cleaning-Internal or Deep Spa job scheduled again is added to the next day's schedule as described in ADM-SCH-26. It is planned like any job of that service, with that service's duration (ADM-SCH-03), and the customer is not charged extra. | Owner and Derived |
| ADM-CNC-04 | The admin is alerted when a job becomes Missed (ADM-ACC-09). This is one of the admin alerts in ADM-SCH-24. The customer sees "Missed. Rescheduled on dd-Mon-yy" once the admin schedules it again (CAL-09 in the customer file). | Derived and Owner |
| ADM-CNC-05 | The outcome and the admin who chose it are recorded with the time. | Derived |

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

---

## 9. Reference data and settings

| ID | Requirement | Status |
|---|---|---|
| ADM-REF-01 | The admin can add, edit and deactivate **societies**: name, sector, city. The customer's society list shows only active societies. A society with active subscriptions or crew cannot be deactivated (ADM-REF-06). | Owner |
| ADM-REF-02 | The "cars serviced" figure shown in the society list is calculated from the active vehicles in that society. | Derived |
| ADM-REF-03 | The admin can maintain the **vehicle catalogue**: makes, models and variants, and the vehicle category for each. They can add, edit and deactivate them. The customer onboarding dropdowns and the auto-detected category come from it (ONB-09, ONB-11). | Owner |
| ADM-REF-04 | The admin can edit a customer's car details: registration number, make, model, variant and category. Customers cannot change these themselves (VEH-04 in the customer file). | Owner |
| ADM-REF-05 | The admin can open a vehicle's uploaded RC document and mark it **Verified**. The customer sees the status in My vehicles (VEH-03). | Derived |
| ADM-SET-01 | **Plans**: the admin keeps a list of plans and can add, edit and deactivate them. For each plan: the plan name, the monthly price, the struck-through list price, the inclusions shown on the review screen (PAY-01, PAY-02), and whether it includes interior cleaning. The interior care day step in the customer's onboarding appears only when the plan includes interior cleaning (ONB-18). The customer chooses one plan when subscribing and when adding a vehicle (PAY-12). A deactivated plan is no longer offered, and subscriptions already on it continue. Only Premium Care exists to start with. Each plan has a unique, permanent plan ID (PLN-0001, PLN-0002 and so on), shown in the Plans list; new plans get the next number. | Owner |
| ADM-SET-02 | **Payment settings**: the UPI ID and the UPI QR code image shown on the payment screen (PAY-05). | Owner |
| ADM-SET-03 | **Support settings**: the helpline number and the WhatsApp number used by "Call support" and "WhatsApp support", and the support hours shown (SUP-02, SUP-03, SUP-04). | Owner |
| ADM-SET-04 | **Invoice settings**: the seller's legal name, address and GSTIN used on the GST invoices (ADM-PAY-08). The values are loaded into the database by an initial seed, and are not edited in the app in MVP. | Owner |
| ADM-REF-06 | A society can be deactivated only when it has no active subscriptions and no active crew. The admin first deactivates those. Deactivating the society then only removes it from the customer's society list. | Owner |

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

## 10. Business rules

1. The admin sets crew working hours and exceptions, so capacity is always known and accurate.
2. Crew roles are Manager, Member and Trainee. Their privileges are in the crew file. Trainees count as zero capacity, are paired with a Member and get that Member's jobs. Members and Managers count in full.
3. Every crew member and every working slot belongs to one society. Capacity and scheduling are worked out for each society.
4. Each service has one or more independent working slots. The defaults are Cleaning-External and Cleaning-Internal 5 AM to 11 AM every day, and Deep Spa every day at any time of day. All are editable. There is no rest day: every day is open.
5. Planning durations: Cleaning-External and Cleaning-Internal about 20 minutes each (one crew member does 3 in 1 hour), Deep Spa 2 hours. The scheduler plans all three.
6. Scheduling only happens when the admin starts it, one period at a time: Daily, Weekly (the default, with the week starting on Sunday) or Monthly. It aims to use the crew's capacity as fully as possible.
7. A draft can be changed by hand and re-run many times. Re-runs keep the changes made by hand and may suggest improvements. Once frozen it can be changed only after entering the secret code, which is the word "unfreeze".
8. When a schedule is frozen, crew can see their assigned cars. Customers see the assigned crew member and time once the visit is assigned.
9. A customer's skip or pause after a freeze applies automatically, and the admin is notified. A cutoff change after a freeze is a request to the admin, who re-runs the scheduler or changes the schedule by hand, and freezes again.
10. A customer can change their own services and schedule settings. The admin can change them too, and the last change wins.
11. Payment statuses are Due, Over due, Initiated and Received. The admin can set any of them. Received closes the record.
12. Admin actions on payments, complaints and schedules are recorded with who and when.
13. Customers and crew use the mobile app. Admins use the web portal, and a limited set of quick actions in the mobile app. The role on each person's login decides what they see and do.
14. Every admin function is on the web portal. Only the simple quick actions in ADM-ACC-07 are in the mobile app, and that list is expected to shrink.
15. A Cleaning-External visit skipped by operations is added to the end of the plan: one day of extension for each day skipped. A skipped Cleaning-Internal job or Deep Spa add-on does not extend the plan.
16. The customer's 9 PM deadline applies to customers only. The admin is not bound by it.
17. A crew member cannot be moved to another society for now.
18. Checklists are set by the admin for each service and only the admin can edit them. The admin also sets the minimum photos and videos for each service.
19. Crew sign in with their mobile number and a generated password that only the admin can reset. A job the crew could not complete is Missed. A Missed Cleaning-External job is covered by the next day's regular job unless the admin skips it by operations. A Missed Cleaning-Internal or Deep Spa job is scheduled again for the next day only, or skipped by operations.
20. A schedule is frozen once, by 8 PM the day before its first day. After a freeze, new visits and redos of Missed jobs are assigned automatically to crew with spare capacity, or go to a Needs scheduling list. Removing work needs no code, adding or moving work does.
21. A billing cycle is 30 calendar days from the first service date. The admin chooses when a subscription becomes Active. An unpaid subscription becomes Inactive after its plan payment has been Over due for 7 days.
22. Sign-in identifiers are unique: a customer's email, a crew member's mobile number and an admin's user ID.
23. The admin can move a payment back to Due or Over due, and generate a GST invoice for a Received payment.
24. Every date shown in the app uses the format dd-Mon-yy, for example 07-Nov-26 (rule 28 in the customer file).
25. Deep Spa is bought separately, as an add-on by a customer with a subscription or as a standalone service by a customer without one. It is planned by the scheduler on the date proposed, and is not dependent on payment status in MVP.

---

## 11. Data entities implied by the requirements

For your reference when you write the data model. This is a reading of the requirements, not a design.

- **User login**: person, login, role (customer, crew, admin). The role decides which screens the app shows.
- **Admin user**: name, user ID (the first is `priveopapa`), password (stored securely, supplied through `.env` at setup). Created by the initial database seed.
- **Customer login**: as in the customer file: email, password hash, email verified, onboarding confirmed. Created when the admin creates the customer.
- **Admin preferences**: scheduling period (Daily, Weekly or Monthly; default Weekly), week start day (Sunday).
- **Cutoff request**: customer's vehicle, old cutoff time, new cutoff time, assigned crew member and time, status (open, handled), handled by and when.
- **Society**: name, sector, city, active flag.
- **Crew member**: name, mobile, society, role (Manager, Member, Trainee), active flag.
- **Working hours**: crew member, day of week, working or off, start time, end time.
- **Exception**: crew member, type (Sick, Leave, Late start), start date, end date, start time (for Late start).
- **Service**: name (Cleaning-External, Cleaning-Internal, Deep Spa), planned duration (20 minutes for Cleaning-External and Cleaning-Internal, 120 minutes for Deep Spa).
- **Working slot**: society, service, days of the week, start time, end time.
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
- **Crew login**: as in the crew file. The admin generates and resets the password and sees whether the login is locked.
- **Session**: login (customer, crew or admin), device name, platform, app version, signed-in time, last-active time, ended time and reason (log out, password reset, deactivation, admin sign-out, inactivity). Used for session management by the admin and for "Sign out of all devices".
- **Checklist**: service, ordered items (name, active flag), minimum photos, minimum videos.
- **Could-not-complete reason**: name, active flag.
- **Could-not-complete record**: as in the crew file, with the admin outcome, handled by and when.
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

---

## 13. Open questions

Open from the crew work and the review:

Resolved 13 Oct 2026: use editable five-step samples for ADM-CHK-07, with mobile read access.
Resolved 13 Oct 2026: standalone Spa uses the same rules as subscriber add-on Spa; see [the owner decisions](owner-decisions-2026-10-13.md).

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

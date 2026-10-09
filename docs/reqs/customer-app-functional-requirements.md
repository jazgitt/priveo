# Priveo Car Concierge: Customer App Functional Requirements

**Status:** Draft v0.5: prototype plus owner decisions of 9 Oct 2026; aligned with the crew requirements (login by role, Missed visits, admin checklists)
**Scope:** Phase 1, Part 1 (Customer), MVP. Admin requirements are in `admin-functional-requirements.md`. Crew requirements are in `crew-functional-requirements.md`.
**Platforms:** iOS and Android (Flutter)
**Language:** English only

## How this document was built

Sources, all in `docs/prototype/`:

- `Priveo Customer App Prototype.html`: interactive prototype (primary source).
- `Screen1.jpeg`, `screen2.jpeg`, `screen3.jpeg`, `screen4.jpeg`: wireframes and UX flow.
- Marketing images and `Car_Concierge_Vision_Deck.pdf`: context only. They contain no screen behavior.
- Owner answers to the open questions, 9 Oct 2026.

Rules followed:

- Only functional features are listed. Business goals, personas, roles, non-functional needs and admin/cleaner features are left for you to add.
- Everything in sections 1 to 11 is **MVP**. Items deferred to the next version are collected in section 15 instead of being mixed into the tables.
- Each requirement has an ID so you can add, remove or reprioritise items without renumbering the rest.
- **Status** column:
  - **Defined**: the prototype shows the behavior working.
  - **Stub**: the prototype only shows a button or toast. The intent is visible but the behavior is not defined.
  - **Wireframe**: shown in the wireframes but not in the interactive prototype.
  - **Owner**: added or changed by an owner decision.
  - **Open**: behavior still undecided, see section 14.
- Where the wireframes and the interactive prototype disagree, the prototype is the source of truth (owner decision). The decisions are listed in section 14.

## Contents

1. Onboarding and authentication
2. Subscription purchase and payment
3. Home
4. Service calendar
5. Service details and proof of service
6. Skip and pause
7. My Account, profile, settings and notifications
8. My subscription
9. My vehicles
10. Support, issues and complaints
11. Navigation
12. Business rules
13. Data entities implied by the screens
14. Conflicts and open questions
15. Deferred to V2 and out of scope

---

## 1. Onboarding and authentication

Flow: Welcome, Mobile number, OTP, Personal details, Society, Vehicle, Parking, Service preferences, Review and pay, Confirmation. Steps 4 to 9 show a progress indicator ("Step N of 6").

| ID | Requirement | Status |
|---|---|---|
| AUTH-01 | Welcome screen with tagline, "Get started" for new users and "Already a member? Log in" for returning users. Both lead to the mobile number screen. | Defined |
| AUTH-02 | The user enters a 10-digit Indian mobile number (+91 prefix fixed). Input is numeric only, grouped as `XXXXX XXXXX`. | Defined |
| AUTH-03 | "Send code" sends a 6-digit OTP by SMS. Invalid number shows an error. | Defined |
| AUTH-04 | Terms and Privacy Policy consent notice is shown on the mobile number screen. | Defined |
| AUTH-05 | OTP screen shows the number the code was sent to, six single-digit boxes, a "Verify" button, and a 30-second resend countdown (00:28 in the prototype). | Defined |
| AUTH-06 | OTP auto-fills from the SMS on the device. | Defined (iPhone shown) |
| AUTH-07 | Resend OTP becomes available when the countdown ends. Invalid OTP shows an error. Maximum 3 to 5 attempts. | Wireframe |
| AUTH-08 | After successful verification, an existing customer goes to the dashboard (Home). A new customer continues to registration. | Wireframe |
| AUTH-10 | Customers, crew and admins all use this same app. Each person has their own login, and the role set for it in the backend decides which screens and actions they see. This file covers the customer screens. The admin screens are in `admin-functional-requirements.md`, and the crew screens are in `crew-functional-requirements.md`. | Owner |
| AUTH-11 | There is one welcome and mobile number screen for everyone. The field takes a mobile number or, for an admin, a user ID. After it is entered the backend decides the method from the role: a customer gets an OTP as described above, a crew member or admin is asked for a password (CRW-ACC-02 in the crew file). The rest of this section describes the customer path. | Owner |
| AUTH-09 | The user can go back from every onboarding screen to edit a previous step. | Defined |

### 1.1 Personal details (Step 1 of 6)

| ID | Requirement | Status |
|---|---|---|
| ONB-01 | Fields: First name (required), Last name (required), Mobile number (pre-filled from login, read-only, shown with a verified indicator). | Defined |
| ONB-02 | First and last name accept only letters, spaces and basic name characters. | Wireframe |

### 1.2 Society (Step 2 of 6)

| ID | Requirement | Status |
|---|---|---|
| ONB-03 | List of societies serviced by Priveo, each showing name, sector/city and number of cars serviced. Only societies Priveo currently serves are listed. | Owner |
| ONB-04 | Search box filters the list as the user types. | Defined |
| ONB-05 | The user selects exactly one society (radio selection). A society is required to continue. | Defined |
| ONB-07 | If no societies are available, show "No serviced societies available at the moment." | Wireframe |

### 1.3 Vehicle (Step 3 of 6)

This step captures the customer's first vehicle. Further vehicles are added later, see section 9.

| ID | Requirement | Status |
|---|---|---|
| ONB-09 | Dropdown fields: Make, Model, Variant (all required). Model depends on Make and Variant on Model. | Defined |
| ONB-10 | Registration number (required), forced to uppercase. Expected format example: `HR26EC4321`. Format validation applies. | Defined |
| ONB-11 | Vehicle category (for example Compact SUV, Large) is detected automatically from the model, shown read-only with an "Auto-detected" indicator. | Defined |
| ONB-12 | Optional RC (registration certificate) upload. Accepted: JPG, PNG, PDF, up to 5 MB. This is a document, so it keeps its own limit and not the photo limit in rule 17. | Defined (upload action is a stub) |
| ONB-22 | Vehicle photo (required). The customer takes it with the camera or picks one from the phone's gallery. The user cannot continue without a photo. Format and size follow rule 17 (section 12); a photo that breaks them is rejected with an error. | Owner |

### 1.4 Parking (Step 4 of 6)

| ID | Requirement | Status |
|---|---|---|
| ONB-13 | Basement selector (B1, B2, B3, B4; required). | Defined |
| ONB-14 | Parking number (required, numeric). | Defined |
| ONB-15 | A visual parking-spot preview updates live (for example "B2 · 123"). An example format is shown for clarity. | Defined |

### 1.5 Service preferences (Step 5 of 6)

| ID | Requirement | Status |
|---|---|---|
| ONB-16 | Service cutoff time (required): the time of day by which the customer wants the daily clean to be finished. The customer sets it with a time picker that allows any time of day in 30-minute steps. The customer does not choose a cleaning slot: slot assignment is done later by the admin (admin feature, Part 2). This replaces the prototype's 2-hour slot picker. The service time the customer sees in the app is this cutoff time. Once the admin has assigned the visit to a crew member, the app shows the assigned crew member and time (CAL-10). Any time can be chosen, even one the crew's working slots cannot meet. The scheduler flags such visits for the admin (ADM-SCH-07) and the customer is not warned. | Owner |
| ONB-17 | A helper note explains that this is the time by which the clean will be done and that Priveo assigns the exact slot. | Owner |
| ONB-18 | Weekly day selection (Monday to Sunday, single choice) for the day on which interior cleaning is added to the exterior clean. Required when the chosen plan includes interior cleaning, and hidden when it does not (ADM-SET-01). The field is called "Interior care day". Deep Spa is not tied to this day: it has its own day (ONB-24). | Defined (conditional on plan: Owner) |
| ONB-20 | Both fields are mandatory. Continuing without them shows inline errors: "Please select your service cutoff time." plus, for the day field, "Please select your interior care day." | Defined |
| ONB-21 | Preferences are saved when the user continues. | Wireframe |
| ONB-24 | **Deep Spa day** (weekday, single choice, Monday to Sunday), shown and required only when the chosen plan includes Deep Spa. One Deep Spa of 2 hours is done in each 30-day plan, on the first such weekday on or after the plan starts. The date can be skipped under SCHED-01, and a skipped Deep Spa is lost for that plan. Continuing without it shows "Please select your Deep Spa day." | Owner and Derived (check) |
| ONB-23 | The plan is chosen in a step before Service preferences (PAY-12), because the plan decides whether the interior care day is asked. The onboarding therefore has one more step than before. | Derived (check) |

### 1.6 Review and confirm (Step 6 of 6)

Covered in section 2.

---

## 2. Subscription purchase and payment

Each vehicle has its own subscription and is paid for separately.

| ID | Requirement | Status |
|---|---|---|
| PAY-01 | Review screen shows the package: name (Premium Care), price (₹999/month, with ₹1,499 struck through), a "Founding member" badge, "Cancel anytime", and the list of inclusions. | Defined |
| PAY-02 | Inclusions shown: exterior cleaning 7 days a week; interior cleaning on the chosen day each week; one full spa (2 hours) in each plan, on the day you choose; weekly tyre dressing and glass treatment; Car Health Check and puncture assistance. | Defined |
| PAY-03 | Summary of everything entered: society, car (make, model, registration), parking (basement and number), service cutoff time, interior day, Deep Spa day (when the plan has them), and the plan. The first service date is not shown here because the admin sets it: the screen says Priveo will confirm the start date. | Defined (first service date: Owner) |
| PAY-04 | Total payable today is shown, inclusive of GST. | Defined |
| PAY-05 | "Confirm & pay" opens a payment screen that shows a UPI QR code for the amount and the Priveo UPI ID (copyable). The customer pays from any UPI app. In MVP this is the only payment method: no card, net banking or payment gateway. | Owner |
| PAY-06 | The payment screen has an "I've paid" button, used when the customer pays offline or by UPI QR/ID. When the customer taps it, the payment status becomes **Initiated** and the payment goes to the admin for confirmation. | Owner |
| PAY-07 | After "I've paid", a confirmation screen shows that the payment has been submitted (status Initiated) and is awaiting confirmation by Priveo, with the amount, the vehicle, and the service details the customer chose. "Go to home" opens Home. | Owner (replaces the prototype's "Payment received" screen) |
| PAY-08 | The admin confirms in the admin screens that the payment was received. The status then becomes **Received** and the payment record is closed. The admin screens are not specified here (Part 2). | Owner |
| PAY-09 | The customer sees one of four payment statuses: **Due by dd-Mon-yy** (for example "Due by 07-Nov-26"), **Over due**, **Initiated** (the customer has marked it paid) and **Received** (the admin has confirmed it). The backend sets the status and the app only displays it. This covers the cases the app does not handle itself, such as a payment the admin cannot find. | Owner |
| PAY-10 | A new subscription is "Activating" until the admin sets the first service date and makes it "Active" (rule 7 in section 12). | Defined (rule: Owner) |
| PAY-12 | The plan step, before Service preferences, lists the plans offered, each with its name, price, struck-through list price and inclusions, loaded from the backend (ADM-SET-01). The customer chooses one plan, for a new customer and when adding a vehicle. Premium Care is the only plan to start with. PAY-01 and PAY-02 describe it. The review screen shows the chosen plan. | Owner |
| PAY-11 | Adding a vehicle later (section 9) ends in the same review and payment steps for that vehicle's own subscription. | Owner |

---

## 3. Home

Home shows the currently selected vehicle. Everything on this screen, and on the calendar, history and skip/pause screens, relates to that vehicle's subscription.

| ID | Requirement | Status |
|---|---|---|
| HOME-01 | Header with Priveo mark and a profile avatar (initials) that opens My Account. Greeting by time of day with the customer's first name. | Defined |
| HOME-02 | Vehicle card: the customer's own vehicle photo from signup (always this photo, not the crew's service photos), registration plate, make and model, variant, society, parking location. | Defined (photo source: Owner) |
| HOME-03 | "Today's clean is done" banner when today's service is complete: completion time, checks completed (for example 5 of 5), number of photos, and a "View proof" action that opens Service Details. | Defined |
| HOME-04 | "Next service" card: status (for example Scheduled), date (for example "Tomorrow, Wed 07-Oct-26"), service type, the service cutoff time, and a "View service calendar" button. Once the visit is assigned, the card also shows the crew member's name and the assigned time (CAL-10). | Defined (assignment: Owner) |
| HOME-05 | Quick actions: Skip or pause, Service history, Rate today's clean (opens Service Details), Report an issue. | Defined |
| HOME-07 | A customer with more than one vehicle can switch the selected vehicle from Home. The selection carries over to the calendar, history, skip/pause and subscription screens. A customer with one vehicle sees no switcher. | Owner |
| HOME-08 | A "Monthly check-in" card appears on Home from 4 days before the renewal date until the customer completes that cycle's check-in (CHK-08). Tapping it opens the check-in. | Owner |

---

## 4. Service calendar

| ID | Requirement | Status |
|---|---|---|
| CAL-01 | Monthly calendar view (Monday-first) with month title. Previous/next arrows move between months. Past months show completed and skipped days; future months show the visits expected from the subscription. The admin schedules crew one period at a time (a week by default), so the crew assignment is not known further ahead. | Owner |
| CAL-02 | Each date has a marker: Exterior done, Exterior + Interior, Full spa, Scheduled (upcoming), Skipped. Interior days show a filled marker when done and an outlined one when upcoming. | Defined |
| CAL-03 | A legend explains the markers. | Defined |
| CAL-04 | Today is highlighted. The selected date is highlighted. | Defined |
| CAL-05 | Selecting a date shows a day card: service type, a status chip (Completed, Scheduled, Skipped, No visit) and a one-line summary (finish time and checks, service cutoff time, "You skipped this date"). | Defined |
| CAL-06 | Tapping the day card for a completed service opens Service Details. Tapping a scheduled day shows "Scheduled to be completed by <cutoff time>. Proof appears after the visit." and, once assigned, the crew member and assigned time (CAL-10). Tapping a skipped day shows "No visit on this day." | Defined |
| CAL-07 | The calendar reflects skips, un-skips, pauses and cutoff-time changes immediately after they are confirmed. | Defined (skip) |
| CAL-09 | A job the crew could not complete is **Missed** (CRW-CNC-04 in the crew file). The calendar shows a Missed marker for that date, and the day card shows "Missed. Rescheduled on dd-Mon-yy" once the admin has scheduled it again (ADM-CNC-03). Before that it shows "Missed". If the admin skips it instead, it shows as Skipped. No push notification is sent for Missed. | Owner |
| CAL-10 | When the admin has assigned a visit to a crew member (the schedule is frozen, or a late visit has been auto-assigned), the Next service card and the day card for that date show the crew member's name and the assigned time. A visit still waiting for a crew member shows as Scheduled with only the cutoff time. If the assignment changes, the new crew member and time are shown. Crew contact details are never shown. | Owner |
| CAL-08 | On a scheduled future date, the day card has a "Change cutoff time" action that sets the cutoff time for that date. It is available until 9 PM the previous day (SCHED-01). | Owner |

---

## 5. Service details and proof of service

| ID | Requirement | Status |
|---|---|---|
| SVC-01 | Header shows the date, a status chip (for example Completed), the service type and finish time. | Defined |
| SVC-02 | One crew member card for each job of the visit (exterior, and interior or spa on an interior day): the crew member's name, "Priveo crew · <society>" and the job. There is no crew rating on the card. | Defined (one card per job, no crew rating: Owner) |
| SVC-03 | Checklist with per-item completion and timestamp, and a summary ("5 of 5 done"). The items come from the checklist the admin set for that service (ADM-CHK-01) and are checked by the crew (CRW-SVC-03). Cleaning-Internal and Deep Spa are separate jobs with their own checklists (ADM-SVS-01). A visit counts as Completed only when all of its jobs are done. Until then it is not Completed, and the completion banner, rating and "Service completed" notification wait for the last job. Service Details shows one crew card for each job (SVC-02), with each job's checklist and proof grouped under it. Prototype items for Cleaning-External: exterior body cleaned, glass cleaned, wheels cleaned, tyres dressed, final inspection. | Defined (source: Owner) |
| SVC-04 | Photo gallery with count, "AFTER" labels on selected photos, and a "View all" action. The crew takes photos after every completed service, and a completed service always has them. | Defined (crew photos after every service: Owner) |
| SVC-05 | Full-screen photo viewer with position counter ("1 / 4"), caption (stage, time, area) and close button. Captions distinguish Before, During and After. | Defined |
| SVC-06 | Video of the service with duration, play-in-place and a progress bar. Videos follow the size limit in rule 17. | Defined |
| SVC-07 | Rating: customer rates the clean from 1 to 5 stars with a single tap. The rating is for the visit as a whole. It is a general rating and is not given to any crew member. A thank-you message confirms it. At 5 stars, positive tags are offered (SVC-11); below 5 stars, issue tags are offered (SVC-14). | Defined |
| SVC-08 | "Report an issue with this clean" opens the report form with the visit pre-linked. | Defined |
| SVC-09 | Service details can be opened for any completed visit from Home, the calendar or the history. | Defined |
| SVC-11 | When the customer gives a visit 5 stars, a short list of positive tags is shown and the customer can pick any of them (optional). Starting tags: **Spotless**, **On time**, **Great tyre finish**. The list is loaded from the backend and is configurable by the admin, like the feedback categories. | Owner |
| SVC-12 | The selected tags are saved with the rating against the visit. They are not tied to a crew member. | Owner |
| SVC-13 | A customer's words are used as a testimonial only with the customer's permission (FDBK-05, SVC-15). | Owner |
| SVC-14 | When the customer gives a visit fewer than 5 stars, the 9 feedback categories (FDBK-06) are offered as issue tags and the customer can pick any that apply (optional). The tags are saved with the rating against the visit. | Owner |
| SVC-15 | The rating flow, at any star level, has an optional comments box and a testimonial permission checkbox, off by default, with the same wording as FDBK-05. | Owner |

### 5.1 Service history

| ID | Requirement | Status |
|---|---|---|
| HIST-01 | List of past services, newest first: date, service type, finish time and the rating given (or none). Each row opens Service Details. | Defined |
| HIST-02 | The list shows one month at a time, starting with the current month. The user can move to earlier months, and long months load in pages. A footer states the month and the member-since date. | Owner |

---

## 6. Skip and pause

Screen with two tabs: "Skip a date" and "Pause service". Both act on the selected vehicle's subscription.

### 6.1 Skip a date

| ID | Requirement | Status |
|---|---|---|
| SKIP-01 | Horizontal date chips for upcoming service days, each showing weekday, day number and service type (Exterior, + Interior, Full spa). | Defined |
| SKIP-02 | Instruction text: skip must be done by 9 PM the evening before. Skip requests after the cutoff are not accepted. | Defined |
| SKIP-03 | The user selects one date, sees a note ("No cleaning on <date>. Your plan isn't charged for this visit.") and taps "Confirm skip". | Defined |
| SKIP-04 | Confirming without a date shows "Pick a date to skip first." | Defined |
| SKIP-05 | On confirm: the date is marked skipped in the upcoming list, calendar and chip; a confirmation says the crew has been told; the crew is notified automatically. | Defined |
| SKIP-06 | An "Upcoming schedule" list below shows the next several dates with type and a Skipped state, plus a "View calendar" link. | Defined |
| SKIP-07 | The customer can undo a skip (un-skip) until 9 PM the previous day (SCHED-01). The date returns to Scheduled, in the list and the calendar, and the crew is told. | Owner |
| SKIP-08 | A date that falls inside a pause cannot be skipped separately. A skip is treated as a subset of a pause (PAUSE-06). | Owner |

### 6.2 Pause service

| ID | Requirement | Status |
|---|---|---|
| PAUSE-01 | The user picks a "From" and "To" date. | Defined |
| PAUSE-02 | A summary shows the number of visits paused and the new renewal date. Paused days are added to the end of the plan: the renewal date moves forward one day for each day paused (rule 26). | Defined |
| PAUSE-03 | "Confirm pause" validates that both dates are set ("Choose the start and end dates first."), then confirms ("Paused 19-Oct-26 to 25-Oct-26. Plan now renews 07-Nov-26."). | Defined |
| PAUSE-04 | Subscription status becomes "Paused" during the pause period. | Defined (see 8) |
| PAUSE-05 | The customer can end an active or upcoming pause early, until 9 PM the previous day (SCHED-01). Visits resume, the status returns to Active, and the renewal date is recalculated to match the days actually paused. | Owner |
| PAUSE-06 | If a pause overlaps dates the customer has already skipped, those skips become part of the pause. Each date is counted once, as a paused day, when the renewal date is moved forward. A skip is by definition a few dates and a pause can be longer. | Owner |
| PAUSE-07 | The "From" date of a pause must still be before its 9 PM cutoff (SCHED-01). No minimum or maximum pause length is set in MVP. | Owner |

### 6.3 Cutoff for schedule changes

| ID | Requirement | Status |
|---|---|---|
| SCHED-01 | Every customer change to a date's schedule must be made by 9 PM the previous day: skip, un-skip, start or end of a pause, and a change of the service cutoff time for a date. | Owner |
| SCHED-02 | After the cutoff, the controls for that date are disabled and the app shows a message to call the helpline for emergency changes, with a "Call support" button (SUP-02). | Owner |

---

## 7. My Account, profile, settings and notifications

### 7.1 Account screen

| ID | Requirement | Status |
|---|---|---|
| ACC-01 | Profile row: avatar with initials, full name, mobile number. Tapping it opens Edit profile (ACC-06). | Defined (tap action: Owner) |
| ACC-02 | Subscription summary card for each vehicle: status chip, plan name, car and society, member-since date, renewal date, monthly amount. Each card opens that vehicle's My subscription. | Defined |
| ACC-03 | Menu: Service calendar, My vehicles, Skip or pause service, Service history, My complaints, Help & support, Settings, Log out. | Defined |
| ACC-04 | Log out. | Stub (disabled in the prototype) |

### 7.2 Edit profile and language

| ID | Requirement | Status |
|---|---|---|
| ACC-06 | The customer can edit their first name, last name and mobile number. Names follow the same validation as onboarding (ONB-01, ONB-02). | Owner |
| ACC-08 | A changed mobile number must be verified with an OTP sent to the new number before it takes effect, because the mobile number is the customer's primary identity. Until it is verified, the old number stays in use for login. | Owner |
| ACC-07 | The app is in English only. There is no language selector. | Owner |

### 7.3 Settings and notifications

| ID | Requirement | Status |
|---|---|---|
| SET-01 | Settings screen opens from the Account menu. | Owner |
| SET-02 | Notification preferences: one on/off switch for each notification event (NOTIF-02). Each can be changed independently. | Owner |
| SET-03 | All switches are on by default for a new customer. | Owner |
| SET-04 | In MVP, Settings holds only the notification switches. | Owner |
| NOTIF-01 | Notifications are push notifications delivered to the customer's phone. The app asks for notification permission from the operating system. | Owner |
| NOTIF-02 | MVP events: **Service completed**, **Service skipped**, **Complaint update** (status change or new update note on a complaint), **Renewal reminder**, **Monthly check-in**. No other events notify in MVP. | Owner |
| NOTIF-03 | A notification is sent only if the customer has that event switched on in Settings. | Owner |
| NOTIF-04 | "Service skipped" is sent both when the customer skips a visit themselves and when a visit is skipped by operations (ADM-OPS-01). A visit the crew could not complete becomes Missed and the admin decides the outcome (ADM-CNC-03): if the admin marks it skipped by operations, this notification is sent. | Owner |
| NOTIF-05 | "Renewal reminder" is a payment reminder with this schedule: the first reminder one week before the renewal date, when "Pay for next month" becomes available (SUB-09); the second reminder one day before; then a reminder every 2 days until the customer marks the payment Initiated, the payment status becomes Received, or the subscription is cancelled. Reminders stop as soon as the customer marks the payment Initiated. If the admin moves the payment back to Due or Over due, the reminders start again (ADM-PAY-07), with no extra notification. It has its own on/off switch in Settings, on by default. Cancelling a subscription is V2. | Owner |
| NOTIF-06 | "Monthly check-in" is sent 4 days before the renewal date to ask the customer to complete the monthly check-in (CHK-01). It has its own on/off switch in Settings, on by default, like the other events. | Owner |

---

## 8. My subscription

Each vehicle has its own subscription. The screen opens for the selected vehicle.

| ID | Requirement | Status |
|---|---|---|
| SUB-01 | Plan card: plan name, status chip, a progress ring with days left in the billing cycle, billing cycle dates, monthly amount and payment method. A billing cycle is 30 calendar days (rule 26). | Defined (cycle length: Owner) |
| SUB-09 | Every monthly payment is manual and started by the customer. From one week before the renewal date, a "Pay for next month" action on this screen opens the same payment screen as PAY-05 (UPI QR code and UPI ID) with the "I've paid" step (PAY-06). The payment then goes to the admin for confirmation like the first one. There is no AutoPay in MVP. | Owner |
| SUB-10 | The screen shows the status of the latest payment: Due by dd-Mon-yy, Over due, Initiated or Received (PAY-09). | Owner |
| SUB-11 | A payment that has been Over due for 7 days makes the subscription Inactive automatically (ADM-SUB-03). The admin can also set it Inactive, and can reactivate it (ADM-SUB-02, ADM-SUB-04). The customer cannot renew an Inactive subscription themselves in MVP. | Owner |
| SUB-02 | Details: car and registration, society, service cutoff time, interior day, Deep Spa day (when the plan has them). | Defined |
| SUB-03 | "Pause service" shortcut opens the skip/pause screen. | Defined |
| SUB-05 | Subscription states: **Active** (membership running), **Activating** (started, waiting for the admin to set the first service date and activate it), **Paused** (paused by customer), **Inactive** (stopped by the admin, or automatically when a payment has been Over due for 7 days). | Defined (Inactive: Owner) |
| SUB-06 | Billing history ("View billing history") lists the subscription's payments, newest first, each with its amount, due date and status (PAY-09). | Wireframe (list: Derived) |
| SUB-12 | For a payment the admin has generated a GST invoice for (ADM-PAY-08), billing history shows an invoice that the customer can open and save. | Owner |
| SUB-08 | The customer can edit the default service cutoff time, the weekly interior day and the Deep Spa day after signup. Each stays required where the plan has it. A change follows the cutoff rule (SCHED-01) and applies from the next date that is still before its 9 PM cutoff. A cutoff time for a single date is changed from the calendar (CAL-08). | Owner |

---

## 9. My vehicles

A customer can own more than one vehicle. Each vehicle has its own parking details, schedule, visits, complaints and subscription.

| ID | Requirement | Status |
|---|---|---|
| VEH-01 | Vehicle photo, mandatory and first captured at signup (ONB-22). It is the photo shown on Home and My vehicles. "Change photo" opens the camera or photo library, and the customer can replace the photo at any time but cannot remove it. Format and size follow rule 17. The crew's service photos are separate and appear only in service proof (SVC-04). | Owner |
| VEH-02 | Read-only vehicle details: registration, make and model, variant, category. | Defined |
| VEH-03 | Parking details: society, basement, parking number, RC document status (Verified). | Defined |
| VEH-04 | Edit parking details. Parking spot and photo are customer-editable; car details change only through support. | Stub (rule stated in the toast) |
| VEH-06 | "My vehicles" lists all of the customer's vehicles, each with registration, make and model, and its subscription status. Tapping one opens its details (VEH-01 to VEH-04). | Owner |
| VEH-07 | "Add vehicle" starts a flow with the same steps as onboarding for a vehicle: society, vehicle details (including the mandatory photo), parking, service preferences, review and payment (section 2). | Owner |
| VEH-09 | A vehicle's society is chosen when the vehicle is added and cannot be changed afterwards. Different vehicles of the same customer can be in different societies. Changing a vehicle's society is for a later phase. | Owner |
| VEH-08 | A newly added vehicle appears in the Home vehicle switcher (HOME-07) once its subscription is created. | Owner |

---

## 10. Support, issues and complaints

### 10.1 Help and support

| ID | Requirement | Status |
|---|---|---|
| SUP-01 | Support screen lists: Frequently asked questions, Report an issue, My complaints (with a count in progress), Give feedback. | Defined |
| SUP-02 | "Call support" opens the phone dialer with the Priveo number. | Stub |
| SUP-03 | "WhatsApp support" opens a WhatsApp chat with the Priveo number. | Stub |
| SUP-04 | Support hours shown: 6 AM to 10 PM. | Defined |
| SUP-05 | FAQ screen, kept simple: a list of questions that expand to show the answer. Topics include billing, skips and damage policy. For now the content lives in a Markdown (.md) file that the app reads, so changing it needs a new app version. Content is supplied by Priveo. | Owner |
| SUP-06 | "Give feedback" opens the feedback modal (FDBK-02). | Owner |

### 10.2 Report an issue

| ID | Requirement | Status |
|---|---|---|
| ISS-01 | Category (single choice, required): Cleaning quality, Missed service, Damage concern, Crew behaviour, Billing, Other. | Defined |
| ISS-02 | Linked visit selector, defaulting to the visit the user came from. | Defined |
| ISS-03 | Description (free text, required). | Defined |
| ISS-04 | Optional photo attachments; the user can add several. Format and size follow rule 17. | Defined |
| ISS-05 | Submitting without a category shows "Choose what went wrong." | Defined |
| ISS-06 | On submit, a complaint is created with a unique ID (format `#C-NNNN`) and a confirmation says a reply comes within 4 hours. The user lands on My complaints with the new item at the top. | Defined |

### 10.3 My complaints

| ID | Requirement | Status |
|---|---|---|
| CMP-01 | List of complaints: ID, status chip, description, raised date and latest update note. | Defined |
| CMP-02 | Statuses and progress bar: Raised, In progress (being handled), Resolved. | Defined |
| CMP-03 | Example update notes: "Supervisor visit booked", "Re-cleaned same day". | Defined |
| CMP-04 | A status change or new update note on a complaint sends a "Complaint update" push notification (NOTIF-02). | Owner |

### 10.4 Feedback

| ID | Requirement | Status |
|---|---|---|
| FDBK-01 | A "side flick" feedback tab sits on the right edge of the screen. It is shown to every customer on every screen, but only after onboarding is completed, never during onboarding. Crew and admins do not see it. The customer can move the tab along the edge but cannot hide it. | Owner |
| FDBK-02 | Tapping the tab (or "Give feedback" in Support) opens a feedback modal with three inputs: a category chosen from the list in FDBK-06, a star rating from 1 to 5, and comments (free text). | Owner |
| FDBK-03 | Submitting shows a confirmation and sends the feedback to the Priveo team. The modal can be closed without submitting. | Owner |
| FDBK-04 | The modal should be well designed and quick to use, with the star rating as a single tap. | Owner |
| FDBK-05 | The modal has a testimonial permission checkbox, off by default: "Priveo may quote my feedback as a testimonial." Priveo uses a customer's words as a testimonial only when this is ticked. | Owner |
| FDBK-06 | The category list is loaded from the backend and is configurable by the admin (admin feature, Part 2). Each category shows a short description as helper text. The starting list is in the table below. | Owner |
| FDBK-07 | At least one response is required before the feedback can be sent: a star rating or a comment. A category alone is not enough. Until then the Send button is disabled. | Owner |

Starting feedback categories:

| Category | What it covers |
|---|---|
| Exterior finish | Streaks, dust left, water marks |
| Glass | Smudges or spots on windshield and windows |
| Wheels and tyres | Rims not cleaned, tyre dressing missing |
| Interior | Dashboard, mats, seats, vacuuming (interior days only) |
| Missed spots | Roof, bumper, door edges |
| Timing | Car not finished by the service cutoff time |
| Care for the car | Mirrors folded or unfolded, doors not locked, worry about scratches |
| Area left clean | Water or cloths left around the parking spot |
| Proof quality | Photos unclear or missing |

### 10.5 Monthly check-in

A monthly check-in that gives Priveo a regular read on how each customer feels about the service. It works like the feedback modal: a list of categories, each with its own 5-star rating, and one optional general comment. It is part of the MVP and is delivered as a push notification.

| ID | Requirement | Status |
|---|---|---|
| CHK-01 | Four days before a vehicle's renewal date, the customer gets a push notification asking them to complete a monthly check-in for that vehicle's subscription (NOTIF-06). | Owner |
| CHK-02 | The check-in lists all active check-in categories (CHK-03), not a selection of them. Each category has its own 1 to 5 star rating, set by tapping a star. The customer may leave a category unrated. | Owner |
| CHK-03 | The check-in categories are the table below. They are categories, not questions, and there is no question bank. The admin can edit the categories (admin feature, Part 2), so the list is loaded from the backend. | Owner |
| CHK-04 | Answers are saved against the vehicle's subscription and the renewal cycle they were given in. | Owner |
| CHK-05 | Tapping the notification opens the check-in. The customer rates the categories and submits, and a thank-you message is shown. | Owner |
| CHK-06 | The check-in has one general comment box for anything extra. It is optional. | Owner |
| CHK-07 | At least one category must be rated before the check-in can be saved. Until then the Submit button is disabled. | Owner |
| CHK-08 | From the day the check-in push is sent, a "Monthly check-in" card is shown on Home until the customer completes the check-in for that renewal cycle. It is shown even when the customer has switched the notification off (HOME-08). | Owner |

Starting check-in categories (CHK-03):

| Category | What it covers |
|---|---|
| Likelihood to recommend | How likely the customer is to recommend Priveo to neighbours. Priveo grows through neighbours in the same society, so this is the key category. |
| Value for money | Whether the service is good value at the current price. |
| Schedule fit | Whether the service cutoff time and the interior day still work for the customer. |
| Crew professionalism | Punctuality, behaviour, uniform. |
| App and support | Whether the proof of service was useful and issues were resolved quickly. |
| Interest in add-ons | Interest in full spa, polish, ceramic coating, car health checks. This also serves as demand research for Phase 2. |

---

## 11. Navigation

| ID | Requirement | Status |
|---|---|---|
| NAV-01 | Bottom tab bar on top-level screens: Home, Calendar, Account, Support. Tabs are hidden during onboarding and on detail screens. | Defined |
| NAV-02 | Detail screens use a back button and return to where the user came from. | Defined |
| NAV-03 | Switching tabs resets the back stack. | Defined |
| NAV-04 | Toast messages confirm actions and report validation problems. | Defined |

---

## 12. Business rules

These are behaviors a developer must implement, taken from the screens and owner decisions:

1. There is no fixed rest day. Every day of the week is open for service, and the admin decides what is scheduled.
2. The plan includes exterior cleaning 7 days a week. On the customer's chosen day the visit also includes interior cleaning. If that day is skipped, paused or skipped by operations, that week's interior cleaning is lost and not made up. Deep Spa is not tied to the interior day: it is done once in each 30-day plan on the customer's Deep Spa day (ONB-24), is 2 hours, and Cleaning-Internal is 20 minutes.
3. Every customer change to a date's schedule (skip, un-skip, start or end of a pause, a new service cutoff time) must be made by 9 PM the previous day. After that the customer calls the helpline for emergency changes. Skipped visits are not charged and the crew is notified automatically.
4. A pause covers a date range, with no minimum or maximum length in MVP. Paused visits are added to the end of the plan, so the renewal date moves forward by the number of visits paused. Ending a pause early recalculates it. A skip is a subset of a pause: skipped dates inside a pause are counted once, as paused days.
5. The customer sets a service cutoff time, the time by which the daily clean must be finished, and does not choose a slot. The admin assigns the actual slot later.
6. The vehicle category is derived from the vehicle model and drives the cleaning routine.
7. A new subscription starts as Activating. The admin sets the first service date and makes it Active, whatever the payment status (ADM-SUB-01). Visits are scheduled only for Active subscriptions.
8. Proof of service per visit: a timed checklist, photos, a video and the crew member's name. The crew takes photos after every completed service.
9. Customer ratings (1 to 5) are tied to a visit and are general: they are not given to any crew member, and crew do not see them.
10. Complaints are acknowledged with a reply within 4 hours.
11. Customers can change parking details, the vehicle photo, the service cutoff time and the interior day themselves; other vehicle details change only through support. A vehicle's society cannot be changed.
12. Prices include GST
13. A customer can own several vehicles. Each vehicle has its own subscription, bought and paid for separately.
14. In MVP, payment is by UPI QR code or UPI ID only. Every monthly payment is manual and started by the customer, from one week before the renewal date. The customer marks it paid (status Initiated), the admin confirms receipt (status Received), and the record is then closed. The statuses shown to the customer are Due by dd-Mon-yy, Over due, Initiated and Received, all set by the backend.
15. In MVP, push notifications are sent for service completed, service skipped (by the customer or by operations), complaint updates, the renewal reminder and the monthly check-in, and only when the customer has the event switched on. All are on by default.
16. The app is in English only.
17. Photos and videos: the app accepts the common formats produced by the camera and gallery on Android and iOS (for example JPEG, PNG and iPhone HEIC). A photo must be under 10 MB and a video under 25 MB. This applies to the vehicle photo, complaint photos and crew service photos and videos. A vehicle photo is mandatory at signup, and the crew takes photos after every completed service. The crew does not use the vehicle photo to identify the car.
18. A payment that has been Over due for 7 days makes the subscription Inactive automatically. The admin can set a subscription Inactive at any time and can reactivate it. An Inactive subscription has no visits and does not count in capacity.
19. A vehicle's society is fixed when the vehicle is added. Each vehicle can be in a different society.
20. The feedback category list and the positive rating tags are configurable by the admin and loaded from the backend, not fixed in the app.
21. A customer's feedback is used as a testimonial only with the customer's permission, which is off by default.
22. Payment reminders: one week before the renewal date, one day before, then every 2 days until the customer marks the payment Initiated, it becomes Received, or the subscription is cancelled.
23. The monthly check-in is a set of admin-editable categories, each rated with 1 to 5 stars, plus one optional comment. At least one category must be rated to save it. It is pushed 4 days before the renewal date and also shown as a card on Home until completed.
24. The feedback modal needs at least a star rating or a comment before it can be sent.
25. A visit skipped by operations is added to the end of the plan. For each day skipped, the plan is extended by one day, so the renewal date moves forward by one day. The customer is not charged extra.
26. A billing cycle is 30 calendar days. The first cycle starts on the first service date. Each later cycle starts on the previous renewal date, so the renewal date is the first day after the 30 days. Pauses (rule 4) and visits skipped by operations (rule 25) move the renewal date forward by one day for each day. A skip by the customer does not move it. The cycle dates shown in the app come from the backend and follow this rule.
27. A job the crew could not complete is Missed. The admin either schedules that job again for the next day only, or marks it skipped by operations (rule 25). A visit is Completed when all of its jobs are done or skipped.
28. Every date shown in the app uses the format dd-Mon-yy, for example 07-Nov-26. This applies to all roles. Weekdays and times are shown as described in each requirement. It cannot be scheduled for any other day. The next day's schedule picks it up before that day's freeze cutoff time (ADM-SCH-26 in the admin file).

---

## 13. Data entities implied by the screens

For your reference when you write the data model. This is a reading of the screens, not a design.

- **Customer**: first name, last name, mobile, avatar initials. Has many vehicles.
- **Society**: name, sector, city, cars serviced. Slots are managed by the admin.
- **Vehicle**: customer, society (fixed), make, model, variant, category, registration number, RC document, photo (mandatory, the customer's own).
- **Parking**: vehicle, basement, parking number.
- **Subscription**: one per vehicle. Customer, vehicle, plan, status (Activating, Active, Paused, Inactive), start date, renewal date, amount, default service cutoff time, interior day, Deep Spa day.
- **Slot assignment**: subscription, assigned slot, assigned crew member, assigned by admin. Set outside the customer app and shown to the customer once assigned.
- **Cutoff override**: subscription, date, cutoff time, for a change to a single date.
- **Service visit**: date, type (Exterior, Exterior + Interior, Full spa), status (Scheduled, Completed, Skipped, Missed), crew member, finish time, rating.
- **Checklist item**: visit, label, completed, completion time.
- **Media**: visit, kind (photo, video), stage (before, during, after), timestamp.
- **Skip / Pause**: subscription, date or date range, status.
- **Complaint**: ID, visit, category, description, photos, status, raised date, update notes.
- **Plan**: name, monthly price, list price, inclusions, active flag. Managed by the admin.
- **Invoice**: payment, invoice number, date, amount and GST breakdown. Generated by the admin.
- **Payment**: subscription, amount, method (UPI QR / UPI ID), due date, status (Due, Over due, Initiated, Received), marked-paid date and time, received date and time, confirming admin. One record per monthly payment.
- **Crew member**: name.
- **Notification preference**: customer, event (service completed, service skipped, complaint update, renewal reminder, monthly check-in), enabled (default on).
- **Device token**: customer, device, push token.
- **Feedback**: customer, category, star rating (1 to 5), comments, testimonial permission (default off), submitted date.
- **Feedback category**: name, description. Managed by the admin. Also used as issue tags on ratings below 5 stars.
- **Positive rating tag**: name. Managed by the admin.
- **Visit rating**: visit, stars, positive tags or issue tags, comments, testimonial permission (default off), rated date and time. Not tied to a crew member.
- **Check-in**: subscription, renewal cycle, star rating per category, general comment, date.
- **Check-in category**: name, description. Managed by the admin.

---

## 14. Conflicts and open questions

### Conflicts (resolved)

Owner decision: where the wireframes and the interactive prototype differ, the prototype is the source of truth. The wireframe versions have been removed from the requirements above.

| # | Topic | Decision (from the prototype) |
|---|---|---|
| C-01 | Weekly day field | Called "Interior care day". Interior cleaning is added on that day. Deep Spa has its own day (ONB-24). |
| C-02 | Plan contents | Interior cleaning once a week, on the chosen day (not 2 days a week). |
| C-03 | Plan price | ₹999 per month, with ₹1,499 shown struck through. The ₹4,999 in one wireframe is dropped. |
| C-04 | Renewal and cycle dates | The dates in the prototype are sample data and are not fixed rules. The prototype's own sample dates do not agree with each other (for example a cycle of 1 to 31 Oct and renewal on 1 Nov, but "renews 7 Nov" after payment). The real dates come from the backend and the billing cycle rule (rule 26 in section 12): 30 calendar days. |
| C-05 | Bottom tab bar | Home, Calendar, Account, Support. Several vehicles are reached through the Home vehicle switcher and "My vehicles" under Account. |
| C-07 | Home quick actions | Skip or pause, Service history, Rate today's clean, Report an issue. "Give feedback" is in Support and on the feedback tab. |
| C-08 | Service Details content | Includes the crew card and the star rating. |

### Open questions

All earlier questions in this file are answered and removed. None of its own are open. Other open questions that touch the customer app are tracked in `admin-functional-requirements.md` and `crew-functional-requirements.md`.

---

## 15. Deferred to V2 and out of scope

### Deferred to V2

| Area | Item |
|---|---|
| Societies | "Launching soon" societies in the society list, and "Can't find your society? Request it"; changing a vehicle's society after it is added |
| Payment | Card, net banking and payment-gateway integrations; UPI AutoPay (all monthly payments are manual until a later phase) and the "Renew automatically" switch; automatic payment confirmation (MVP relies on the admin confirming); failed or cancelled payment handling and retry; refunds; automatic receipts (admin-generated GST invoices are in MVP, SUB-12) |
| Subscription | Cancelling a subscription; changing plan ("Change plan"); renewing an inactive subscription |
| Support | FAQ content managed outside an app release (for now it is a Markdown file) |
| Complaints | Complaint detail view; replies from the Priveo team; reopening a complaint |
| Account | Account deletion |
| Accessibility | Accessibility options |

### Out of scope

- Vehicle ownership changes (transferring a vehicle to another customer).
- Languages other than English.

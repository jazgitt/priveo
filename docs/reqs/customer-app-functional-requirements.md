# Priveo Car Concierge: Customer App Functional Requirements

**Status:** Draft v0.23 (Deep Spa and My Subscription landing pages; calendar greys only days without a subscription; Expires on; Renew subscription and the payment method choice; next service stays until the crew closes it; calendar plan-duration line; calendar limited to the billing cycle; complaint confirmation has no 4-hour promise; skip screen changes; refresh on return only after 5 minutes away; one combined vehicle card; no timed refresh, 16 Oct 2026; feedback tab is an icon only; 30-minute code): wireframe-only rows re-statused to Derived; prototype plus owner decisions of 9 Oct 2026; customers sign in by email; Deep Spa is an add-on for subscribers and a standalone service for others (owner decision of 10 Oct 2026); consistency pass
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
  - **Derived**: needed to make a stated item work and not shown in the prototype. Please check it.
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
9a. Add-ons (Deep Spa)
10. Support, issues and complaints
11. Navigation
12. Business rules
13. Data entities implied by the screens
14. Conflicts and open questions
15. Deferred to V2 and out of scope

---

Owner decisions of 13 Oct 2026 supersede earlier fixed-policy/undecided wording; see [the decision record](owner-decisions-2026-10-13.md).

## 1. Onboarding and authentication

Flow for a customer the admin has created: Welcome, Email, Verification code (first sign-in only), Set password (first sign-in only), then the onboarding review (Personal details, Society, Vehicle, Parking, Service preferences, Plan and review), then Home. A returning customer goes Welcome, Email, Password, Home. In MVP the admin creates the customer and fills in the details, so prospective customers do not enter them themselves (AUTH-14).

| ID | Requirement | Status |
|---|---|---|
| AUTH-01 | Welcome screen with tagline, "Get started" and "Already a member? Log in". Both lead to the email screen. | Defined |
| AUTH-02 | The user enters their email address. The email is checked for a valid format and is not case sensitive. The prototype shows a mobile number here. | Owner |
| AUTH-03 | "Continue" checks the email against the customers the admin has created (AUTH-14). If the customer has not yet set a password, a 6-digit verification code is sent to the email and the code screen opens. If a password is set, the password screen opens. An invalid email format shows an error. | Owner |
| AUTH-04 | Terms and Privacy Policy consent notice is shown on the email screen. The customer's acceptance is recorded with the date and time at first sign-in, including for customers the admin created. | Defined (record: Derived) |
| AUTH-05 | The code screen shows the email the code was sent to, six single-digit boxes, a "Verify" button, and a 30-second resend countdown (00:28 in the prototype). A code is valid for 30 minutes. | Defined (email, 30 minutes: Owner) |
| AUTH-06 | The user can paste the code from the clipboard. The code does not auto-fill from an SMS, as the prototype shows. | Owner and Derived |
| AUTH-07 | Resend becomes available when the countdown ends. A wrong code shows an error. After 5 wrong attempts the code is cancelled and the user must request a new one. At most 5 codes can be requested in an hour. | Derived (numbers: Owner) |
| AUTH-08 | After a correct code, a customer with no password sets one (AUTH-12). Then, if the customer has not yet confirmed the onboarding review (ONB-25), the review opens. Otherwise Home opens. | Owner |
| AUTH-10 | Customers and crew use this app. Admins use a web portal, and a limited set of admin quick actions is also in this app. Each person has their own login, and the role set for it in the backend decides which screens and actions they see. This file covers the customer screens. The admin requirements are in `admin-functional-requirements.md`, and the crew screens are in `crew-functional-requirements.md`. | Owner |
| AUTH-11 | There is one welcome and sign-in screen for everyone. The field takes an email (customer), a 10-digit mobile number (crew) or a user ID (admin). The backend decides the method from what is entered: a customer gets an emailed code on first sign-in and then uses a password, and a crew member or admin is asked for a password (CRW-ACC-02 in the crew file). The rest of this section describes the customer path. | Owner |
| AUTH-12 | After the code is verified, the customer sets a password and confirms it. A password has at least 8 characters, with a letter and a number. The customer cannot continue without one. | Owner |
| AUTH-13 | A returning customer signs in with email and password. A wrong password shows an error. After 5 wrong attempts sign-in is blocked for 15 minutes, and the customer can use "Forgot password". | Owner |
| AUTH-14 | In MVP only customers the admin has created can sign in. Prospective customers do not enter their own details: the admin creates the customer with their email (ADM-CUS-01), and the customer then verifies the email, sets a password and reviews the details (ONB-25). Open public signup is V2 (section 15). | Owner |
| AUTH-15 | If the email is not one the admin has created, the app shows "This email is not registered. Contact Priveo", with "Call support" and "WhatsApp support" buttons (SUP-02, SUP-03). No code is sent. | Owner |
| AUTH-16 | "Forgot password": the customer enters their email and, if the admin has created it, a 6-digit code is sent. After the code is verified the customer sets a new password (AUTH-12). The old password stops working. | Owner and Derived |
| AUTH-17 | The app keeps the customer signed in on the phone, with no inactivity time-out. The customer signs in again only after logging out, after the password is changed or reset, after the admin signs them out (ADM-CUS-21), or on a new phone or after a reinstall. | Owner and Derived |
| AUTH-09 | The user can go back from every onboarding screen to edit a previous step. | Defined |

### 1.1 Personal details (Step 1 of 7)

| ID | Requirement | Status |
|---|---|---|
| ONB-01 | Fields: First name (required), Last name (required), Email (read-only, shown with a verified indicator), Mobile number (required contact number, not verified; the customer can correct it). The admin has usually filled these in already. | Defined (email, mobile: Owner) |
| ONB-25 | **Onboarding review.** In MVP the admin creates the customer and fills in the details (ADM-CUS-01). When the customer first signs in, the onboarding steps (personal details, society, vehicle, parking, service preferences, plan and review) open with those details filled in. The customer goes through each step, completes anything the admin left empty, and confirms on the last step. Home opens only after the customer confirms. | Owner |
| ONB-26 | In the review the customer can change what they can normally change: names, mobile number, parking, vehicle photo, service cutoff time and interior day. The society, the vehicle details (make, model, variant, registration, category) and the plan are shown but can be changed only by Priveo (VEH-04, VEH-09, ADM-REF-04), so the society selection and the vehicle dropdowns (ONB-03 to ONB-11) are used when a customer adds a vehicle or, in V2, signs up publicly. | Owner |
| ONB-02 | First and last name accept only letters, spaces and basic name characters. | Derived |

### 1.2 Society (Step 2 of 7)

| ID | Requirement | Status |
|---|---|---|
| ONB-03 | List of societies serviced by Priveo, each showing name, sector/city and number of cars serviced. Only societies Priveo currently serves are listed. | Owner |
| ONB-04 | Search box filters the list as the user types. | Defined |
| ONB-05 | The user selects exactly one society (radio selection). A society is required to continue. | Defined |
| ONB-07 | If no societies are available, show "No serviced societies available at the moment." | Derived |

### 1.3 Vehicle (Step 3 of 7)

This step captures the customer's first vehicle. Further vehicles are added later, see section 9.

| ID | Requirement | Status |
|---|---|---|
| ONB-09 | Dropdown fields: Make, Model, Variant (all required). Model depends on Make and Variant on Model. | Defined |
| ONB-10 | Registration number (required), forced to uppercase. Expected format example: `HR26EC4321`. Format validation applies. | Defined |
| ONB-11 | Vehicle category (for example Compact SUV, Large) is detected automatically from the model, shown read-only with an "Auto-detected" indicator. | Defined |
| ONB-12 | Optional RC (registration certificate) upload. Accepted: JPG, PNG, PDF, up to 5 MB. This is a document, so it keeps its own limit and not the photo limit in rule 17. | Defined (upload action is a stub) |
| ONB-22 | Vehicle photo (required). The customer takes it with the camera or picks one from the phone's gallery. The user cannot continue without a photo. Format and size follow rule 17 (section 12); a photo that breaks them is rejected with an error. | Owner |

### 1.4 Parking (Step 4 of 7)

The plan is Step 5 of 7 (ONB-23, PAY-12).

| ID | Requirement | Status |
|---|---|---|
| ONB-13 | Basement selector (B1, B2, B3, B4; required). | Defined |
| ONB-14 | Parking number (required, numeric). | Defined |
| ONB-15 | A visual parking-spot preview updates live (for example "B2 · 123"). An example format is shown for clarity. | Defined |

### 1.5 Service preferences (Step 6 of 7)

| ID | Requirement | Status |
|---|---|---|
| ONB-16 | Service cutoff time (required): the time of day by which the customer wants the daily clean to be finished. The customer sets it with a time picker that allows any time of day in 30-minute steps. The customer does not choose a cleaning slot: slot assignment is done later by the admin (admin feature, Part 2). This replaces the prototype's 2-hour slot picker. The service time the customer sees in the app is this cutoff time. Once the admin has assigned the visit to a crew member, the app shows the assigned crew member and time (CAL-10). Any time can be chosen, even one the crew's working slots cannot meet. The scheduler flags such visits for the admin (ADM-SCH-07) and the customer is not warned. | Owner |
| ONB-17 | A helper note explains that this is the time by which the clean will be done and that Priveo assigns the exact slot. | Owner |
| ONB-18 | Weekly day selection (Monday to Sunday, single choice) for the day on which interior cleaning is added to the exterior clean. Required when the chosen plan includes interior cleaning, and hidden when it does not (ADM-SET-01). The field is called "Interior care day". | Defined (conditional on plan: Owner) |
| ONB-20 | Both fields are mandatory where they are shown. Continuing without them shows inline errors: "Please select your service cutoff time." plus, for the day field when the plan has interior cleaning, "Please select your interior care day." | Defined |
| ONB-21 | Preferences are saved when the user continues. | Derived |
| ONB-23 | When a customer adds a vehicle, the plan is chosen in a step before Service preferences (PAY-12), because the plan decides whether the interior care day is asked. In the onboarding review the plan step shows the plan the admin chose, read-only. The onboarding therefore has one more step than before. | Owner |

### 1.6 Review and confirm (Step 7 of 7)

Covered in section 2.

---

## 2. Subscription purchase and payment

Each vehicle has its own subscription and is paid for separately.

| ID | Requirement | Status |
|---|---|---|
| PAY-01 | Review screen shows the package: name (Premium Care), price (₹999/month, with ₹1,499 struck through), a "Founding member" badge, "Cancel anytime", and the list of inclusions. | Defined |
| PAY-02 | Inclusions shown: exterior cleaning 7 days a week; interior cleaning on the chosen day each week; weekly tyre dressing and glass treatment; Car Health Check and puncture assistance. Deep Spa is not a plan inclusion: it is an add-on (section 9a). | Defined (Deep Spa: Owner) |
| PAY-03 | Summary of everything entered: society, car (make, model, registration), parking (basement and number), service cutoff time, interior day (when the plan has it), and the plan. The first service date is not shown here because the admin sets it: the screen says Priveo will confirm the start date. | Defined (first service date: Owner) |
| PAY-04 | Total payable today is shown, inclusive of GST. | Defined |
| PAY-05 | "Confirm & pay" opens a payment screen that shows a UPI QR code for the amount and the Priveo UPI ID (copyable). The customer pays from any UPI app. The screen shows a Payment method choice with UPI selected by default and Credit card shown disabled ("Coming soon"). In MVP UPI is the only working method: no card, net banking or payment gateway. The screen gives three steps: copy the UPI ID, pay the amount to it from any UPI app, then tap "I've paid" to submit the confirmation. A plan payment's screen is titled "Renew subscription"; other payments keep "Pay by UPI". | Owner (17 Oct 2026) |
| PAY-06 | The payment screen has an "I've paid" button, used when the customer pays offline or by UPI QR/ID. When the customer taps it, the payment status becomes **Initiated** and the payment goes to the admin for confirmation. | Owner |
| PAY-07 | After "I've paid", a confirmation screen shows that the payment has been submitted (status Initiated) and is awaiting confirmation by Priveo, with the amount, the vehicle, and the service details the customer chose. "Go to home" opens Home. | Owner (replaces the prototype's "Payment received" screen) |
| PAY-08 | The admin confirms that the payment was received. The status then becomes **Received** and the payment record is closed (ADM-PAY-03). | Owner |
| PAY-09 | The customer sees one of four payment statuses: **Due by dd-Mon-yy** (for example "Due by 07-Nov-26"), **Over due**, **Initiated** (the customer has marked it paid) and **Received** (the admin has confirmed it). The backend sets the status and the app only displays it. This covers the cases the app does not handle itself, such as a payment the admin cannot find. | Owner |
| PAY-10 | A new subscription is "Activating" until the admin sets the first service date and makes it "Active" (rule 7 in section 12). | Defined (rule: Owner) |
| PAY-12 | The plan step lists the plans offered, each with its name, price, struck-through list price and inclusions, loaded from the backend (ADM-SET-01). The customer chooses one plan when adding a vehicle (and, in V2, at public signup). For a customer the admin created, the plan is the one the admin chose and is shown on the review, not chosen. Premium Care is the only plan to start with. PAY-01 and PAY-02 describe it. | Owner |
| PAY-13 | For a customer the admin created, the status of the first payment is set by the admin (ADM-CUS-06). On the review step, if the first payment is Due or Over due, "Confirm & pay" opens the UPI screen described in PAY-05 to PAY-07. If it is Initiated or Received, the step shows the status and asks for no payment. | Owner |
| PAY-11 | Adding a vehicle later (section 9) ends in the same review and payment steps for that vehicle's own subscription. | Owner |

---

## 3. Home

Home shows the currently selected vehicle. Everything on this screen, and on the calendar, history and skip/pause screens, relates to that vehicle's subscription.

| ID | Requirement | Status |
|---|---|---|
| HOME-01 | Header with Priveo mark and a profile avatar (initials) that opens My Account. Greeting by time of day with the customer's first name. | Defined |
| HOME-02 | One vehicle card holds the vehicle and its service details, with no separate service card below it. From the top: the customer's own vehicle photo from signup (always this photo, not the crew's service photos) as a picture across the card, or a default illustrated car if there is no photo; the registration plate with the subscription status (Active, Paused and so on) at the top right; make, model and variant; the subscription plan name with its monthly price; society and parking location; then "Expires on <date>" (the plan's last covered day, SUB-01), the society and parking slot on one line separated by a comma, then the next service (HOME-04). A vehicle with no subscription shows "No subscription" and no next service. | Owner (16 Oct 2026) |
| HOME-03 | "Today's clean is done" banner when today's service is complete: completion time, checks completed (for example 5 of 5), number of photos, and a "View proof" action that opens Service Details. | Defined |
| HOME-04 | "Next service" section inside the vehicle card (HOME-02): status (for example Scheduled), date (for example "Tomorrow, Wed 07-Oct-26"), service type, and the cutoff time as "Planned before your cutoff time - 7:00 AM". Once the visit is assigned, it also shows the crew member's name and the assigned time (CAL-10). A "View service calendar" button sits below the vehicle card, outside it. The visit stays as the next service until the crew marks it Completed or Missed, so at 1 AM the service due that day is still shown, not the next day's. Skipped and paused days are passed over; the next service is the next day that is neither. | Owner (17 Oct 2026; assignment: Owner) |
| HOME-05 | Quick actions: Skip or pause, Service history, Rate today's clean (opens Service Details), Report an issue. | Defined |
| HOME-07 | A customer with more than one vehicle can switch the selected vehicle from Home. The selection carries over to the calendar, history, skip/pause and subscription screens. A customer with one vehicle sees no switcher. | Owner |
| HOME-08 | A "Monthly check-in" card appears on Home from 4 days before the renewal date until the customer completes that cycle's check-in (CHK-08). Tapping it opens the check-in. | Owner |
| HOME-09 | An "Add-ons" card on Home opens the add-on list (ADD-02). It is shown only for a vehicle with an Active subscription. | Owner |
| HOME-10 | The app does not refresh screens on a timer. Data is read when a screen opens, and once when the app returns to the foreground after being in the background for 5 minutes or more. A shorter absence refreshes nothing. A refresh never shows a loading state or flash: the current data stays on screen until the new data arrives. A loading indicator shows only on the first load of a screen. A bottom tab that has been opened stays loaded, so going back to it shows its data at once. | Owner |

---

## 4. Service calendar

| ID | Requirement | Status |
|---|---|---|
| CAL-01 | Monthly calendar view (Monday-first) with month title. Previous/next arrows move between months. Past months show completed and skipped days; future months show the visits expected from the subscription. The admin schedules crew one period at a time (a week by default), so the crew assignment is not known further ahead. | Owner |
| CAL-02 | Each date has a marker: Exterior done, Exterior + Interior, Full spa (a day with an add-on), Scheduled (upcoming), Skipped, Missed. Interior days show a filled marker when done and an outlined one when upcoming. | Defined |
| CAL-03 | A legend explains the markers. Days when the customer had no subscription (before it started or after it expired) are greyed out and cannot be selected. Every day the subscription has covered stays selectable with its status markers, including earlier months. No action is allowed on a past date. Under the "Service calendar" headline, a line shows the plan duration and status (for example "Plan duration: 11-Nov-26 to 10-Dec-26 · Active"). | Owner (18 Oct 2026) |
| CAL-04 | Today is highlighted. The selected date is highlighted. | Defined |
| CAL-05 | Selecting a date shows a day card: service type, a status chip (Completed, Scheduled, Skipped, Missed, No visit) and a one-line summary (finish time and checks, service cutoff time, "You skipped this date"). | Defined |
| CAL-06 | Tapping the day card for a completed service opens Service Details. Tapping a scheduled day shows "Scheduled to be completed by <cutoff time>. Proof appears after the visit." and, once assigned, the crew member and assigned time (CAL-10). Tapping a skipped day shows "No visit on this day." | Defined |
| CAL-07 | The calendar reflects skips, un-skips, pauses and cutoff-time changes immediately after they are confirmed. After the schedule is frozen, a change of cutoff time or add-on date is only a request: the calendar and day card keep the current value and show "Change requested, awaiting Priveo" until the admin acts (ADM-SCH-22, ADM-SCH-31). | Defined (skip); Owner (after a freeze) |
| CAL-09 | A job the crew could not complete is **Missed** (CRW-CNC-04 in the crew file). The calendar shows a Missed marker for that date. The day card shows "Missed", and then: for a Cleaning-External job, "Missed. Covered on dd-Mon-yy" (the next day's regular visit); for a Cleaning-Internal or Deep Spa job the admin has scheduled again, "Missed. Rescheduled on dd-Mon-yy". If the admin skips it instead, it shows as Skipped. No push notification is sent for Missed. | Owner and Derived |
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

Screen with two tabs: "Skip a date" and "Pause service". Both act on the selected vehicle's subscription. "Pause service" on My subscription (SUB-03) opens this screen on the Pause tab. A skip or pause updates every screen that shows the schedule (Home, the service calendar, My subscription, this screen) without a visible reload.

### 6.1 Skip a date

| ID | Requirement | Status |
|---|---|---|
| SKIP-01 | Horizontal date chips for upcoming service days, each showing weekday, day number and service type (Exterior, + Interior). The text of a chip shows its status: Skipped in yellow, Paused in red, Completed in green. | Owner (status colours, 16 Oct 2026) |
| SKIP-02 | There is no instruction text above the date chips. Skip requests after the 9 PM cutoff are not accepted. When the next day is already past the cutoff, it starts selected and the screen shows "The cutoff for <date> has passed (9 PM the evening before). Please call support for an emergency change." with a Call support button. Picking another day clears the message; picking the closed day shows it again, and it cannot be skipped. | Owner (16 Oct 2026) |
| SKIP-03 | The user selects one date and taps "Confirm skip". No note about charges is shown. A skipped day does not change the plan: no day is added to it and the renewal date does not move (only a pause or a visit skipped by operations does, PAUSE-02, ADM-OPS-03). | Owner (16 Oct 2026) |
| SKIP-04 | Confirming without a date shows "Pick a date to skip first." | Defined |
| SKIP-05 | On confirm: the date is marked skipped in the upcoming list, calendar and chip; a confirmation says the crew has been told; the crew is notified automatically. | Defined |
| SKIP-06 | The screen has no upcoming-schedule list. A "View Service Calendar" button below opens the service calendar. This button has the same label and look everywhere it appears in the app. | Owner (16 Oct 2026) |
| SKIP-07 | The customer can undo a skip (un-skip) until 9 PM the previous day (SCHED-01). The date returns to Scheduled, in the list and the calendar, and the crew is told. | Owner |
| SKIP-08 | A date that falls inside a pause cannot be skipped separately. A skip is treated as a subset of a pause (PAUSE-06). | Owner |

### 6.2 Pause service

| ID | Requirement | Status |
|---|---|---|
| PAUSE-01 | The user picks a "From" and "To" date. | Defined |
| PAUSE-02 | A summary shows the number of visits paused and the new renewal date. Paused days are added to the end of the plan: the renewal date moves forward one day for each day paused (rule 26). | Defined |
| PAUSE-03 | "Confirm pause" validates that both dates are set ("Choose the start and end dates first."), then confirms ("Paused 19-Oct-26 to 25-Oct-26. Plan now renews 07-Nov-26."). | Defined |
| PAUSE-04 | Subscription status becomes "Paused" during the pause period. | Defined (see 8) |
| PAUSE-05 | The customer can end an active or upcoming pause early, until 9 PM the previous day (SCHED-01). Visits resume, the status returns to Active, and the renewal date is recalculated to match the days actually paused. A pause that ends today or tomorrow has nothing left to end: the message says "That pause ends today already." or "That pause ends tomorrow already." to match. | Owner |
| PAUSE-06 | If a pause overlaps dates the customer has already skipped, those skips become part of the pause. Each date is counted once, as a paused day, when the renewal date is moved forward. A skip is by definition a few dates and a pause can be longer. | Owner |
| PAUSE-07 | The "From" date of a pause must still be before its 9 PM cutoff (SCHED-01). No minimum or maximum pause length is set in MVP. | Owner |

### 6.3 Cutoff for schedule changes

| ID | Requirement | Status |
|---|---|---|
| SCHED-01 | Every customer change to a date's schedule must be made by 9 PM the previous day: skip, un-skip, start or end of a pause, a change of the service cutoff time for a date, and a change or cancellation of an add-on (ADD-10). | Owner |
| SCHED-02 | After the cutoff, the controls for that date are disabled and the app shows a message to call the helpline for emergency changes, with a "Call support" button (SUP-02). | Owner |

---

## 7. My Account, profile, settings and notifications

### 7.1 Account screen

| ID | Requirement | Status |
|---|---|---|
| ACC-01 | Profile row: avatar with initials, full name, mobile number. Tapping it opens Edit profile (ACC-06). | Defined (tap action: Owner) |
| ACC-02 | Subscription summary card for each vehicle: status chip, plan name, car and society, member-since date, renewal date, monthly amount. Each card opens that vehicle's My subscription. | Defined |
| ACC-03 | Menu: Service calendar, My vehicles, Add-ons, Skip or pause service, Service history, My complaints, Help & support, Settings, Log out. | Defined |
| ACC-04 | Log out. | Stub (disabled in the prototype) |

### 7.2 Edit profile and language

| ID | Requirement | Status |
|---|---|---|
| ACC-06 | The customer can edit their first name, last name and mobile number. Names follow the same validation as onboarding (ONB-01, ONB-02). The mobile number is a contact detail and needs no verification. | Owner |
| ACC-08 | A changed email must be verified with a 6-digit code sent to the new email before it takes effect, because the email is the customer's sign-in identity. Until it is verified, the old email stays in use. The new email must not already belong to another customer. | Owner |
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
| NOTIF-05 | "Renewal reminder" is a payment reminder with this schedule: the first reminder one week before the renewal date, when "Pay for next month" becomes available (SUB-09); the second reminder one day before; then a reminder every 2 days until the customer marks the payment Initiated, the payment status becomes Received, or the subscription becomes Inactive. Reminders stop as soon as the customer marks the payment Initiated. If the admin moves the payment back to Due or Over due, the reminders start again (ADM-PAY-07), with no extra notification. It has its own on/off switch in Settings, on by default. | Owner |
| NOTIF-06 | "Monthly check-in" is sent 4 days before the renewal date to ask the customer to complete the monthly check-in (CHK-01). It has its own on/off switch in Settings, on by default, like the other events. | Owner |

---

## 8. My subscription

Each vehicle has its own subscription. The screen opens for the selected vehicle.

| ID | Requirement | Status |
|---|---|---|
| SUB-01 | Plan card: plan name, status chip, a progress ring with days left in the billing cycle, billing cycle dates, monthly amount and payment method. A billing cycle is 30 calendar days (rule 26). The plan card also shows "Expires on <date>", the last day the plan covers. It is the end of the current cycle, and it moves 30 days further as soon as the admin confirms a renewal payment (SUB-09), even before the renewal date. Days left count to the expiry date. Home and the service calendar use the same expiry date. | Defined (cycle length: Owner; expiry on confirmation: Owner, 17 Oct 2026) |
| SUB-09 | Every monthly payment is manual and started by the customer. From 7 days before the renewal date (the admin setting "Days before renewal a payment is created", default 7), a "Renew subscription" action on this screen opens the same payment screen as PAY-05 (UPI QR code and UPI ID) with the "I've paid" step (PAY-06). The payment then goes to the admin for confirmation like the first one. There is no AutoPay in MVP. | Owner |
| SUB-10 | The screen shows the status of the latest payment: Due by dd-Mon-yy, Over due, Initiated or Received (PAY-09). | Owner |
| SUB-11 | A plan payment that has been Over due for 7 days makes the subscription Inactive automatically (ADM-SUB-03). An Over due add-on payment does not. The admin can also set it Inactive, and can reactivate it (ADM-SUB-02, ADM-SUB-04). The customer cannot renew an Inactive subscription themselves in MVP. | Owner |
| SUB-02 | Details: car and registration, society, service cutoff time, interior day (when the plan has it). | Defined |
| SUB-03 | "Pause service" shortcut opens the Skip or pause screen on its Pause tab. | Owner (17 Oct 2026) |
| SUB-05 | Subscription states: **Active** (membership running), **Activating** (started, waiting for the admin to set the first service date and activate it), **Paused** (paused by customer), **Inactive** (stopped by the admin, or automatically when a plan payment has been Over due for 7 days). | Defined (Inactive: Owner) |
| SUB-06 | Billing history ("View billing history") lists the subscription's payments, newest first, each with its amount, due date and status (PAY-09). | Derived |
| SUB-12 | For a payment the admin has generated a GST invoice for (ADM-PAY-08), billing history shows an invoice that the customer can open and save. | Owner |
| SUB-13 | My Subscription is a service landing page that shows what the customer pays for: a hero card with the plan name, status, price a month (with the list price struck through), days left and the date the plan runs until; "What you get" (the plan's inclusions); the vehicle, service cutoff time and interior day; the plan details with the plan ID; the latest payment; and "Your add-ons", the add-ons booked for this vehicle that the crew has not yet completed (Requested or Scheduled). | Owner (18 Oct 2026) |
| SUB-08 | The customer can edit the default service cutoff time and the weekly interior day after signup. Each stays required where the plan has it. A change follows the cutoff rule (SCHED-01) and applies from the next date that is still before its 9 PM cutoff. A cutoff time for a single date is changed from the calendar (CAL-08). | Owner |

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
| VEH-07 | "Add vehicle" starts a flow with the same steps as onboarding for a vehicle: society, vehicle details (including the mandatory photo), parking, plan, service preferences, review and payment (section 2). | Owner |
| VEH-09 | A vehicle's society is chosen when the vehicle is added and cannot be changed afterwards. Different vehicles of the same customer can be in different societies. Changing a vehicle's society is for a later phase. | Owner |
| VEH-08 | A newly added vehicle appears in the Home vehicle switcher (HOME-07) once its subscription is created. | Owner |

---

## 9a. Add-ons (Deep Spa)

An add-on is an optional extra service the customer buys separately from the plan. In MVP the only add-on is Deep Spa, a 2-hour job. A customer with a subscription buys it as an add-on. A customer without a subscription can take Deep Spa as a standalone service (ADD-14). The rows ADD-01 to ADD-13 describe the add-on path in the app.

| ID | Requirement | Status |
|---|---|---|
| ADD-01 | In the app, an add-on is bought for a vehicle whose subscription is Active. A pause blocks only the dates it covers: a Deep Spa can be booked for a date after the pause ends, even while the pause is running. For a vehicle that is Activating, Paused or Inactive the add-on screens are hidden. Deep Spa is not part of any plan. Deep Spa without a subscription is the standalone service (ADD-14). | Owner and Derived |
| ADD-02 | The customer finds add-ons on the Home "Add-ons" card (HOME-09) and in an "Add-ons" item in the Account menu (ACC-03). The screen lists the add-ons offered, each with its name, description, price including GST and struck-through list price, loaded from the backend (ADM-ADD-01). It also lists the customer's earlier add-on requests with their status. | Owner |
| ADD-03 | The customer can buy any number of add-ons. Each purchase is its own request, with its own payment. | Owner |
| ADD-04 | To buy, the customer chooses the add-on, proposes **one preferred date** and a **finish-by time**, and confirms. The date must be tomorrow or later and still before its 9 PM cutoff (SCHED-01). The finish-by time is any time of day in 30-minute steps. A summary shows the vehicle, add-on, date, time and total. | Owner |
| ADD-05 | "Confirm & pay" opens the same UPI payment screen as PAY-05 to PAY-07, for the add-on's price. The customer pays from any UPI app and taps "I've paid". The payment is separate from the plan payment, uses the same four statuses (PAY-09), is confirmed by the admin, and can have a GST invoice (SUB-12, ADM-PAY-08). | Owner |
| ADD-06 | In MVP scheduling does not depend on the payment status. The request is planned as soon as it is made, whatever its payment status. This may change later. | Owner |
| ADD-07 | An add-on request has a status: **Requested** (made, waiting to be scheduled), **Scheduled** (a crew member and time are assigned), **Completed**, **Cancelled** and **Missed** (the crew could not do it). | Derived |
| ADD-08 | The scheduler plans the add-on as a job of its own duration (2 hours for Deep Spa) on the proposed date, in the crew's capacity and before that day's freeze cutoff (ADM-SCH-30). Once planned, the status is Scheduled and the customer sees the assigned crew member and time (CAL-10). | Owner |
| ADD-09 | If the scheduler cannot fit the job on the proposed date, the request goes to the admin's Needs scheduling list (ADM-SCH-28) and stays **Requested**. The admin agrees a new date with the customer and sets it (ADM-ADD-03). The app never changes the date by itself. | Owner |
| ADD-10 | Until 9 PM the day before the date, the customer can change the date or the finish-by time, or cancel the request (SCHED-01). After the cutoff the controls are disabled and the app shows the "Call support" message (SCHED-02). If the schedule is already frozen, a change of date or time is a request and shows "Change requested, awaiting Priveo" (CAL-07). A cancelled add-on is not charged. Any refund of an amount already paid is handled by the admin outside the app (refunds are V2). | Owner |
| ADD-11 | A scheduled add-on appears on the calendar on its date with the Full spa marker (CAL-02) and a day card. When the job is done, its proof (checklist, photos, video, crew member) opens in Service Details like any job (SVC-01 to SVC-06). The add-on job is separate from the day's plan visit: the plan visit completes without waiting for it. | Owner |
| ADD-12 | If the crew could not do the job, it is Missed. The admin schedules it again for the next day only, or marks it skipped by operations: a skipped Deep Spa does not extend the plan, and any refund or rebooking is handled by the admin outside the app (ADM-CNC-03, ADM-OPS-03). The customer sees "Missed. Rescheduled on dd-Mon-yy" as in CAL-09. | Derived |
| ADD-13 | No new notification event is added in MVP. "Service completed" applies when the add-on job is done (NOTIF-02). | Derived |
| ADD-14 | Deep Spa is not only an add-on. A customer who has no subscription can take Deep Spa as a standalone service. | Owner |
| ADD-15 | Admin creates the customer and vehicle without a subscription. The customer books, pays for and follows standalone Deep Spa using the same rules as subscriber add-on Spa (owner decision 13 Oct 2026). | Owner |
| ADD-16 | The Deep Spa screen is one service landing page, titled "Deep Spa", for subscribers and for customers without a subscription. It shows the service name, a short pitch, the price (list price struck through), the duration, and "What's included". The first line of the add-on's description in the catalogue is the pitch; every further line is shown as an inclusion. The words "Deep Spa without a subscription" are not shown. | Owner (18 Oct 2026) |

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
| ISS-06 | On submit, a complaint is created with a unique ID (format `#C-NNNN`) and a confirmation says "Your Issue has been received. We will respond back asap" (no time is promised). The user lands on My complaints with the new item at the top. | Defined |

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
| FDBK-01 | A "side flick" feedback tab sits on the right edge of the screen. It is a small icon only, with no visible text ("Feedback" is its screen-reader label). It is shown to every customer on every screen, but only after onboarding is completed, never during onboarding. Crew and admins do not see it. The customer can move the tab along the edge but cannot hide it. | Owner |
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
2. The plan includes exterior cleaning 7 days a week. On the customer's chosen day the visit also includes interior cleaning. If that day is skipped, paused or skipped by operations, that week's interior cleaning is lost and not made up. Deep Spa is not part of the plan: a subscriber buys it separately as an add-on, and a customer without a subscription can take it as a standalone service (section 9a).
3. Every customer change to a date's schedule (skip, un-skip, start or end of a pause, a new service cutoff time, an add-on change or cancellation) must be made by 9 PM the previous day. After that the customer calls the helpline for emergency changes. Skipped visits are not charged and the crew is notified automatically.
4. A pause covers a date range, with no minimum or maximum length in MVP. Paused visits are added to the end of the plan, so the renewal date moves forward by the number of visits paused. Ending a pause early recalculates it. A skip is a subset of a pause: skipped dates inside a pause are counted once, as paused days.
5. The customer sets a service cutoff time, the time by which the daily clean must be finished, and does not choose a slot. The admin assigns the actual slot later.
6. The vehicle category is derived from the vehicle model and drives the cleaning routine.
7. A new subscription starts as Activating. The admin sets the first service date and makes it Active, whatever the payment status (ADM-SUB-01). Visits are scheduled only for Active subscriptions.
8. Proof of service per visit: a timed checklist, photos, a video and the crew member's name. The crew takes photos after every completed service.
9. Customer ratings (1 to 5) are tied to a visit and are general: they are not given to any crew member, and crew do not see them.
10. Complaints are acknowledged with a reply as soon as possible. No reply time is promised to the customer.
11. Customers can change parking details, the vehicle photo, the service cutoff time and the interior day themselves; other vehicle details change only through support. A vehicle's society cannot be changed.
12. Prices include GST
13. A customer can own several vehicles. Each vehicle has its own subscription, bought and paid for separately.
14. In MVP, payment is by UPI QR code or UPI ID only. Every monthly payment is manual and started by the customer, from one week before the renewal date. The customer marks it paid (status Initiated), the admin confirms receipt (status Received), and the record is then closed. The statuses shown to the customer are Due by dd-Mon-yy, Over due, Initiated and Received, all set by the backend. A plan payment is created 7 days before the renewal date and is due on it. An add-on payment is due on the day the add-on is requested and goes Over due the next day if unpaid.
15. In MVP, push notifications are sent for service completed, service skipped (by the customer or by operations), complaint updates, the renewal reminder and the monthly check-in, and only when the customer has the event switched on. All are on by default.
16. The app is in English only.
17. Photos and videos: the app accepts the common formats produced by the camera and gallery on Android and iOS (for example JPEG, PNG and iPhone HEIC). A photo must be under 10 MB and a video under 25 MB. This applies to the vehicle photo, complaint photos and crew service photos and videos. A vehicle photo is mandatory at signup, and the crew takes photos after every completed service. The crew does not use the vehicle photo to identify the car.
18. A plan payment that has been Over due for 7 days makes the subscription Inactive automatically. An Over due add-on payment does not. The admin can set a subscription Inactive at any time and can reactivate it. An Inactive subscription has no visits and does not count in capacity.
19. A vehicle's society is fixed when the vehicle is added. Each vehicle can be in a different society.
20. The feedback category list and the positive rating tags are configurable by the admin and loaded from the backend, not fixed in the app.
21. A customer's feedback is used as a testimonial only with the customer's permission, which is off by default.
22. Payment reminders: one week before the renewal date, one day before, then every 2 days until the customer marks the payment Initiated, it becomes Received, or the subscription becomes Inactive.
23. The monthly check-in is a set of admin-editable categories, each rated with 1 to 5 stars, plus one optional comment. At least one category must be rated to save it. It is pushed 4 days before the renewal date and also shown as a card on Home until completed.
24. The feedback modal needs at least a star rating or a comment before it can be sent.
25. A Cleaning-External visit skipped by operations is added to the end of the plan. For each day skipped, the plan is extended by one day, so the renewal date moves forward by one day. The customer is not charged extra. A skipped Cleaning-Internal job is lost for that week and does not extend the plan. A skipped Deep Spa add-on does not extend the plan: any refund or rebooking is handled by the admin outside the app.
26. A billing cycle is 30 calendar days. The first cycle starts on the first service date. Each later cycle starts on the previous renewal date, so the renewal date is the first day after the 30 days. Pauses (rule 4) and visits skipped by operations (rule 25) move the renewal date forward by one day for each day. A skip by the customer does not move it. The cycle dates shown in the app come from the backend and follow this rule.
27. A job the crew could not complete is Missed. A Missed Cleaning-External job is covered by the next day's regular job unless the admin skips it by operations. A Missed Cleaning-Internal or Deep Spa job is scheduled again by the admin for the next day only, or skipped by operations (rule 25). It cannot be scheduled for any other day. A visit is Completed when all of its jobs are done or skipped.
28. Every date shown in the app uses the format dd-Mon-yy, for example 07-Nov-26. This applies to all roles. Weekdays and times are shown as described in each requirement.
29. A customer signs in with their email. The customer exists only because the admin created them. At the first sign-in they get a 6-digit code by email, set a password, and review the details the admin entered. After that they sign in with email and password, and stay signed in on the phone. Forgot password and an email change use an emailed code. There is no mobile OTP.
30. In MVP prospective customers do not sign themselves up. An email the admin has not created gets no code and sees "This email is not registered. Contact Priveo."
31. Deep Spa (2 hours) is sold in two ways. A customer with a subscription buys it as an add-on for a vehicle with an Active subscription. A customer without a subscription can take it as a standalone service; they use the same booking/payment/service rules after admin-created onboarding (ADD-15). For an add-on, the customer proposes one date and a finish-by time, pays by UPI, and the scheduler plans the job. Scheduling does not wait for payment in MVP. The customer can change or cancel until 9 PM the day before.

---

## 13. Data entities implied by the screens

For your reference when you write the data model. This is a reading of the screens, not a design.

- **Customer**: first name, last name, email (sign-in identity, unique), mobile (contact, not verified), password (stored hashed), email verified, terms accepted date, onboarding confirmed, avatar initials. Has many vehicles.
- **Verification code**: customer, purpose (first sign-in, forgot password, email change), code (stored hashed), expiry, wrong attempts, sent time.
- **Add-on**: name, description, price, list price, duration, active flag. Managed by the admin. Deep Spa is the first.
- **Add-on request**: customer, vehicle (with or without a subscription), add-on, proposed date, finish-by time, status (Requested, Scheduled, Completed, Cancelled, Missed), assigned crew member and time, payment, created and changed times.
- **Society**: name, sector, city, cars serviced. Slots are managed by the admin.
- **Vehicle**: customer, society (fixed), make, model, variant, category, registration number, RC document, photo (mandatory, the customer's own).
- **Parking**: vehicle, basement, parking number.
- **Subscription**: one per vehicle. Customer, vehicle, plan, status (Activating, Active, Paused, Inactive), start date, renewal date, amount, default service cutoff time, interior day.
- **Slot assignment**: subscription, assigned slot, assigned crew member, assigned by admin. Set outside the customer app and shown to the customer once assigned.
- **Cutoff override**: subscription, date, cutoff time, for a change to a single date.
- **Service visit**: date, type (Exterior, Exterior + Interior), status (Scheduled, Completed, Skipped, Missed), crew member, finish time, rating.
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
| C-01 | Weekly day field | Called "Interior care day". Interior cleaning is added on that day. |
| C-02 | Plan contents | Interior cleaning once a week, on the chosen day (not 2 days a week). |
| C-03 | Plan price | ₹999 per month, with ₹1,499 shown struck through. The ₹4,999 in one wireframe is dropped. |
| C-04 | Renewal and cycle dates | The dates in the prototype are sample data and are not fixed rules. The prototype's own sample dates do not agree with each other (for example a cycle of 1 to 31 Oct and renewal on 1 Nov, but "renews 7 Nov" after payment). The real dates come from the backend and the billing cycle rule (rule 26 in section 12): 30 calendar days. |
| C-05 | Bottom tab bar | Home, Calendar, Account, Support. Several vehicles are reached through the Home vehicle switcher and "My vehicles" under Account. |
| C-07 | Home quick actions | Skip or pause, Service history, Rate today's clean, Report an issue. "Give feedback" is in Support and on the feedback tab. |
| C-08 | Service Details content | Includes the crew card and the star rating. |

### Open questions

All earlier questions in this file are answered and removed. One is open:

Resolved 13 Oct 2026: standalone Deep Spa follows ADD-15 and the [owner decisions](owner-decisions-2026-10-13.md).

Other open questions that touch the customer app are tracked in `admin-functional-requirements.md` and `crew-functional-requirements.md`.

---

## 15. Deferred to V2 and out of scope

### Deferred to V2

| Area | Item |
|---|---|
| Societies | "Launching soon" societies in the society list, and "Can't find your society? Request it"; changing a vehicle's society after it is added |
| Sign-up | Open public signup and self-onboarding: any email can get a code and prospective customers enter their own details |
| Add-ons | Add-ons other than Deep Spa; add-ons for a vehicle that is not Active; scheduling that waits for payment (MVP has no dependency on payment status); refunds for cancelled add-ons |
| Payment | Card, net banking and payment-gateway integrations; UPI AutoPay (all monthly payments are manual until a later phase) and the "Renew automatically" switch; automatic payment confirmation (MVP relies on the admin confirming); failed or cancelled payment handling and retry; refunds; automatic receipts (admin-generated GST invoices are in MVP, SUB-12) |
| Subscription | Cancelling a subscription; changing plan ("Change plan"); renewing an inactive subscription |
| Support | FAQ content managed outside an app release (for now it is a Markdown file) |
| Complaints | Complaint detail view; replies from the Priveo team; reopening a complaint |
| Account | Account deletion |
| Accessibility | Accessibility options |

### Out of scope

- Vehicle ownership changes (transferring a vehicle to another customer).
- Languages other than English.

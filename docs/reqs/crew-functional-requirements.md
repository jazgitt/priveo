# Priveo Car Concierge: Crew App Functional Requirements

**Status:** Draft v0.1: owner decisions of 9 Oct 2026
**Scope:** Phase 1, Part 3 (Crew), MVP. Customer requirements are in `customer-app-functional-requirements.md`. Admin requirements are in `admin-functional-requirements.md`.
**Platforms:** The same Flutter app as the customer and admin, with screens chosen by the user's role.
**Language:** English only

## How this document was built

Sources:

- The crew rules you gave on 9 Oct 2026 (items a to g) and your answers to four design questions.
- The customer and admin requirements files, for the rules the crew features must respect or that already depend on a crew feature.

Rules followed:

- Each requirement has an ID. Crew IDs start with `CRW-`.
- **Status** column:
  - **Owner**: you stated it.
  - **Derived**: not stated, but needed to make a stated item work, or taken from the customer or admin requirements. Please check these.
  - **Open**: depends on a question in section 11.
- Everything in this file is **MVP** unless section 12 says otherwise.
- Only functional features are listed.
- Role privileges are covered: Member (the common features here), Trainee (section 3, CRW-SCH-10) and Manager (section 3a).

## Contents

1. Access and login
2. Profile
3. My schedule (job cards)
3a. Manager features
4. Performing a service
5. Could not complete
6. Ratings received
7. Notifications
8. Business rules
9. Data entities implied by the requirements
10. Customer and admin requirements and the crew features that cover them
11. Open questions
12. Deferred to V2 and out of scope

---

## 1. Access and login

| ID | Requirement | Status |
|---|---|---|
| CRW-ACC-01 | Crew use the same app as customers and admins. The role set on their login in the backend decides which screens they see. | Owner |
| CRW-ACC-02 | There is one welcome and login screen for everyone. The screen has one field that takes an email, a mobile number or a user ID. An email belongs to a customer, a 10-digit mobile number to a crew member, and anything else is looked up as an admin user ID. A customer gets an emailed code on first sign-in and then uses a password. A crew member or admin is asked for a password. | Owner |
| CRW-ACC-03 | A crew member's login ID is their mobile number. They cannot change it. | Owner |
| CRW-ACC-04 | When the admin onboards a crew member, the password is generated automatically in this format: the first 3 letters of their name, then 4 random digits, then `$` (for example `Raj4821$`). | Owner |
| CRW-ACC-05 | Passwords are never sent by SMS or WhatsApp. After the admin onboards a crew member or resets their password, the admin screen shows the login ID and the generated password once, with a Copy button, and the admin gives them to the crew member outside the app. The app stores only a hash, so the password cannot be shown again. | Owner |
| CRW-ACC-06 | Crew cannot change their password. If it is lost, the admin resets it: a new password is generated in the same format and shown to the admin once (CRW-ACC-05, ADM-CRW-18 in the admin file). | Owner (reset: Derived) |
| CRW-ACC-07 | A wrong password shows an error. After a set number of wrong attempts the login is locked until the admin resets the password. The number of attempts is not decided. | Open |
| CRW-ACC-08 | A deactivated crew member cannot sign in (ADM-CRW-15). Their past visits and records stay. | Derived |
| CRW-ACC-09 | Log out. | Derived |
| CRW-ACC-10 | A mobile number can belong to only one crew member (ADM-CRW-06). A customer's email or contact mobile number has no effect on crew sign-in. | Owner |

**Known risk:** the password format is easy to guess (a name prefix, 4 digits and a fixed symbol), and crew cannot change it. The admin reset is the only remedy. This is recorded as a risk, not changed.

---

## 2. Profile

| ID | Requirement | Status |
|---|---|---|
| CRW-PRF-01 | The crew member can view their profile: photo, name, mobile number, society, role, and working hours (read-only). | Owner and Derived |
| CRW-PRF-02 | The crew member can edit basic details. For now this is the profile photo (camera or photo library). More editable fields will be added when needed. | Owner |
| CRW-PRF-03 | The crew member cannot edit their login ID (mobile number) or password. Name, society and role are set by the admin. | Owner |
| CRW-PRF-04 | The profile photo follows the photo format and size rule (rule 17 in the customer file). | Derived |

---

## 3. My schedule (job cards)

| ID | Requirement | Status |
|---|---|---|
| CRW-SCH-01 | The crew member sees their scheduled jobs as job cards, one for each assigned vehicle. Jobs appear once the admin freezes a schedule (ADM-SCH-20). | Owner |
| CRW-SCH-02 | A job card shows: the vehicle (registration, make, model, category), the society, the parking spot (basement and number), the assigned slot time, the service to be done, and the job status. | Owner |
| CRW-SCH-03 | The card also shows the vehicle photo the customer gave at signup, to help the crew find the car. The crew does not use it to identify the car (rule 17 in the customer file). | Derived |
| CRW-SCH-04 | The card shows the customer's service cutoff time as the time the job must be finished by. The customer sees the assigned crew member and time once the visit is assigned (CAL-10 in the customer file), but never the crew's notes or contact details. | Owner |
| CRW-SCH-05 | The service shown is Cleaning-External for every visit. On the customer's interior care day there is also a separate job for Cleaning-Internal or Deep Spa (ADM-SVS-01). Each job has its own job card, checklist, proof and completion, and can be done by a different crew member. The scheduler plans these jobs with their own durations: 20 minutes for Cleaning-Internal and 2 hours for Deep Spa (ADM-SVS-09, ADM-SVS-10), so the card shows the assigned start and end time for each. | Owner and Open |
| CRW-SCH-06 | The crew member can view the cards day by day, or all of the jobs scheduled so far. | Owner |
| CRW-SCH-07 | Job statuses: **Scheduled**, **In progress** (started and not finished), **Completed**, **Could not complete**. | Derived |
| CRW-SCH-08 | When a customer skips or pauses after the schedule is frozen, the visit is removed from the crew member's cards automatically (ADM-SCH-21). | Derived |
| CRW-SCH-09 | When the admin unfreezes, changes and freezes the schedule again, or the system assigns a late visit automatically (ADM-SCH-27), the crew member's cards update to match. | Derived |
| CRW-SCH-10 | A Member sees only their own jobs. A Trainee is paired with a Member (ADM-CRW-19) and sees the same jobs as that Member. A Trainee can do everything a Member can: check the checklist, upload proof, mark a job complete or Could not complete. A Trainee counts as zero capacity and is never assigned a job by the scheduler (ADM-CRW-14). | Owner |
| CRW-SCH-12 | A job is one job, whoever does it. When the Member or the Trainee marks it complete, it is complete for both, and each sees the other's checklist ticks and uploads. If the paired Member has an exception for the day (sick, leave, late start), the Trainee has no jobs until the Member does. | Derived (check) |
| CRW-SCH-13 | No crew member sees a customer's name or mobile number on a job card or anywhere else in the crew app. Cards show the vehicle, society and parking spot only. | Owner |
| CRW-SCH-11 | Jobs from a schedule that is still a draft are not shown. | Derived |

---

## 3a. Manager features

A Manager is a crew member with the Manager role. Managers count in full capacity (ADM-CAP-02), so they also do jobs as a Member does. A Manager can act only on their own society. Everything a Manager changes is recorded with their name and the time (ADM-CRW-20).

| ID | Requirement | Status |
|---|---|---|
| CRW-MGR-01 | A Manager can see the whole society's schedule, read-only: every crew member's job cards and job statuses, by day and by crew member. | Owner |
| CRW-MGR-02 | A Manager can mark a job assigned to another crew member as **Could not complete** (with a reason, CRW-CNC-02) or as **skipped**. A job marked skipped by a Manager is a visit skipped by operations: the customer gets the "Service skipped" notification if it is switched on, and the plan is extended by one day (ADM-OPS-03). | Owner and Derived |
| CRW-MGR-03 | A Manager can reassign a job to another Member or Manager of the same society who is working that day. The admin's secret code is not needed. The job moves to the other crew member's cards, a Trainee paired with either follows their Member, and both crew members get a push notification. The reassignment is recorded. | Owner and Derived |
| CRW-MGR-04 | A Manager can see crew attendance for their society and can add, edit and remove exceptions (Sick, Leave, Late start) for its crew members (ADM-CRW-08). Capacity is recalculated at once (ADM-CRW-11), and the affected visits go to the Needs scheduling list (ADM-SCH-28) or are auto-assigned (ADM-SCH-27). | Owner and Derived |
| CRW-MGR-05 | A Manager cannot change working hours, roles, passwords or schedules, and cannot freeze or unfreeze a schedule. Those stay with the admin. | Derived (check) |
| CRW-MGR-06 | A Manager does not see a customer's name or mobile number (CRW-SCH-13). | Owner |

---

## 4. Performing a service

| ID | Requirement | Status |
|---|---|---|
| CRW-SVC-01 | Opening a job card shows the job details (CRW-SCH-02) and the checklist for the service being done. | Owner |
| CRW-SVC-02 | The checklist is the one the admin set up for that service (ADM-CHK-01). The crew member cannot add, remove or change items. | Owner |
| CRW-SVC-03 | The crew member checks each item as they do it. Each check records the time. These checks and times appear in the customer's Service Details (SVC-03 in the customer file). | Owner and Derived |
| CRW-SVC-04 | The crew member uploads photos and a video of the serviced vehicle. The camera and the phone's gallery can both be used. | Owner |
| CRW-SVC-05 | Each photo and video is labelled with a stage: Before, During or After. The labels appear in the customer's photo viewer (SVC-05). | Derived |
| CRW-SVC-06 | Formats and sizes follow rule 17 in the customer file: common camera formats including iPhone HEIC, photos under 10 MB, videos under 25 MB. A file that breaks them is rejected with an error. | Derived |
| CRW-SVC-07 | The admin sets the minimum number of photos and videos for each service (ADM-CHK-06). | Owner |
| CRW-SVC-08 | "Mark complete" works only when every checklist item is checked and the minimum photos and videos have been uploaded. Until then it is disabled and the screen shows what is missing. | Owner |
| CRW-SVC-09 | On "Mark complete" the finish time is saved and the job becomes Completed. When all the jobs of the visit are Completed, the visit becomes Completed: the customer then gets a "Service completed" push notification if they have it switched on (NOTIF-02 in the customer file), and the proof appears in their app. | Owner and Derived |
| CRW-SVC-10 | If the connection is poor, photos and videos wait on the phone and upload when the connection returns, without being lost. The job is not complete for the customer until everything has uploaded. | Derived |
| CRW-SVC-11 | A crew member can start a job any time after it appears and can leave and return to it before marking it complete. Their progress is kept. | Derived |
| CRW-SVC-12 | After a job is marked Completed the crew member cannot change it. Corrections go through the admin. | Derived |

---

## 5. Could not complete

| ID | Requirement | Status |
|---|---|---|
| CRW-CNC-01 | A crew member who cannot do a job can mark it **Could not complete**. | Owner |
| CRW-CNC-02 | They choose a reason from a list and can add a note and a photo. The reason is required, the note and photo are optional. | Owner and Derived |
| CRW-CNC-03 | The reason list is managed by the admin (ADM-CNC-01). A starting list is in the admin file. | Derived |
| CRW-CNC-04 | The job status becomes **Could not complete** and the job is **Missed** in the system. The other jobs of the visit are not affected. The admin is told by push notification (ADM-SCH-24). | Derived |
| CRW-CNC-05 | The admin decides what happens next: schedule the job again for the next day only, or mark it skipped by operations, which extends the plan by one day (ADM-CNC-03). A job scheduled again appears on the crew member's cards for the next day once that schedule is frozen. | Owner and Derived |
| CRW-CNC-06 | The customer sees "Missed. Rescheduled on dd-Mon-yy" once the job is scheduled again, and no push notification is sent (CAL-09 in the customer file). | Owner |

---

## 6. Ratings received

| ID | Requirement | Status |
|---|---|---|
| CRW-RAT-01 | Customer ratings are general ratings of the visit. They are not given to any crew member, and the crew app does not show ratings, tags or customer comments (SVC-07, SVC-12 in the customer file). | Owner |

---

## 7. Notifications

| ID | Requirement | Status |
|---|---|---|
| CRW-NOT-01 | The crew member receives a push notification when a schedule is frozen with new or changed jobs for them. | Derived |
| CRW-NOT-02 | The crew member receives a push notification when a job is removed from their cards because of a skip, a pause, or a visit skipped by operations. | Derived |
| CRW-NOT-05 | A crew member (and a Trainee paired with them) gets a push notification when a Manager reassigns a job to or from them (CRW-MGR-03). | Derived |
| CRW-NOT-04 | The crew member receives a push notification when a job is assigned to them automatically after a freeze (ADM-SCH-27). The job appears on their cards. | Owner |
| CRW-NOT-03 | Crew cannot switch these notifications off. There are no other crew notifications in MVP. | Derived |

These are proposals for you to check. Today the admin file says the admin gets the only notifications of this kind.

---

## 8. Business rules

1. Crew, customers and admins use one app. The role on the login decides what each person sees.
2. A crew member signs in with their mobile number and the generated password. They cannot change either. The admin can reset the password.
3. The crew member's role is to do the service. They see only the jobs assigned to them, and only once the admin freezes the schedule.
4. Once a visit is assigned, the customer sees the assigned crew member and time. The crew sees the slot and also the customer's cutoff time as the finish-by time. No crew member sees a customer's name or mobile number.
5. Each service has a checklist set by the admin, and only the admin can edit it.
6. A job is complete only when every checklist item is checked and the admin's minimum photos and videos are uploaded.
7. Photo and video limits follow rule 17 in the customer file.
8. A job that cannot be done is marked Could not complete with a reason. The visit is Missed and the admin decides the outcome.
9. A completed job cannot be changed by the crew.
10. A crew member belongs to one society and is deactivated by the admin when they leave.
11. Every date shown in the app uses the format dd-Mon-yy, for example 07-Nov-26 (rule 28 in the customer file).

---

## 9. Data entities implied by the requirements

For your reference when you write the data model. This is a reading of the requirements, not a design.

- **Crew login**: mobile number (login ID), password (stored securely), role (crew), active flag, last password reset by and when.
- **Crew member**: as in the admin file, with profile photo.
- **Job card**: a view of a scheduled visit for one crew member (visit, vehicle, parking, assigned time, service, status).
- **Checklist progress**: visit, checklist item, checked, time checked.
- **Media**: visit, kind (photo, video), stage (Before, During, After), time, uploaded by.
- **Could-not-complete record**: visit, reason, note, photo, crew member, time, admin outcome and handled by.
- **Could-not-complete reason**: name, active flag. Managed by the admin.

---

## 10. Customer and admin requirements and the crew features that cover them

| Needed by | Crew capability | Covered by |
|---|---|---|
| ADM-SCH-20: crew see assigned cards when the schedule is frozen | My schedule | CRW-SCH |
| ADM-SCH-21: skip or pause after a freeze removes the visit | Cards update automatically | CRW-SCH-08 |
| ADM-CRW-04, ADM-CRW-17: crew are onboarded with working hours and a login | Login and password | CRW-ACC |
| ADM-CHK: checklists, minimum proof and reasons | Checklist, uploads and Could not complete | CRW-SVC, CRW-CNC |
| SVC-03, SVC-04, SVC-05, SVC-06: checklist, photos and video in Service Details | Crew capture and upload | CRW-SVC |
| NOTIF-02 and NOTIF-04: "Service completed" and "Service skipped" notifications | Mark complete, Could not complete | CRW-SVC-09, CRW-CNC |
| SVC-02: one crew card for each job in Service Details | The crew member assigned to each job | CRW-SCH |

---

## 11. Open questions

1. How many wrong passwords lock an account (CRW-ACC-07)?
2. (Answered: sign-in identifiers are unique, and customers now use email.)
3. (Answered: the scheduler plans them with 20 and 120 minutes, ADM-SVS-10.)
4. (Answered: a Trainee is paired with a Member and does everything a Member does.)
5. (Answered: see CAL-09.)
6. (Answered: crew do not see ratings or comments.)
7. Do you agree with the crew notifications in section 7?
8. (Answered: privileges are in this file.)

---

## 12. Deferred to V2 and out of scope

### Deferred to V2

| Area | Item |
|---|---|
| Account | Crew changing their own password; forced password change on first login |
| Crew tools | Crew-initiated skips, leave requests, or swapping jobs between crew |

### Out of scope for this file

- The starting checklists for Cleaning-Internal and Deep Spa (ADM-CHK-07), to be supplied by the owner.
- Scheduling of Cleaning-Internal and Deep Spa (ADM-SVS-10).

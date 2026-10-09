# CLAUDE.md

Priveo Car Concierge: a subscription car-care service for housing societies. A Flutter app (iOS and Android) serves customers and crew, with a small set of admin quick actions. Admins use a React web portal. Screens are chosen by the role on the login. See `README.md` for the product summary.

## State of the repo

Requirements and prototype material only. There is no application code, build or test setup yet. The work so far is writing and refining the three functional requirements files in `docs/reqs/`, and drafting the stack in `docs/tech-stack.md`. When code is added, update this file with the build and test commands.

## Tech stack (decided by the owner)

Flutter (Riverpod, go_router, feature folders) for the app. Python FastAPI with PostgreSQL for the API, with the scheduler (OR-Tools) in the same service. AWS Mumbai (ECS Fargate, RDS, S3, EventBridge Scheduler) for hosting. Resend for email (verification codes, password reset codes, welcome email). FCM for push. S3 signed uploads for media with an offline upload queue in the app. A React web portal for admin, with every admin function in MVP, and a limited set of admin quick actions in the Flutter app. Details, supporting choices and risks are in `docs/tech-stack.md`. All choices there are decided; the risks section lists what to watch.

## Layout

- `docs/reqs/customer-app-functional-requirements.md`: customer app
- `docs/reqs/admin-functional-requirements.md`: admin (functional requirements for the web portal and the mobile quick actions)
- `docs/reqs/crew-functional-requirements.md`: crew
- `docs/tech-stack.md`: technical stack (all choices decided)
- `tools/priveo-reqs/`: a Claude Code mod for the requirements files. It checks IDs after each edit, guards `docs/prototype/` and `.env`, and adds `/ids`, `/open`, `/synccheck`, `/fstatus` and `/priveo-status` (a side pane with the stage counts and open bugs). `/fstatus` tracks each requirement ID through Draft, Approved, Ready for Dev, In Dev, Unit Tested >95%, Functional Tested and Security Test, with an open-bug count, in `docs/feature-status.json`. A new or changed requirement row goes back to Draft. Load it with `claude --plugin-dir tools/priveo-reqs`. Test it with `claude plugin test tools/priveo-reqs`.
- `docs/prototype/`: interactive prototype HTML, wireframes, vision deck, marketing images. Read-only source material. The prototype HTML is about 1 MB, so search it with grep instead of reading it whole.

## Rules for editing the requirements

- **Owner decisions win.** Where the prototype or a wireframe disagrees with an owner decision, the requirements follow the owner. The prototype's known differences are listed in `README.md`. Keep that list current when a decision makes the prototype more out of date.
- **Do not decide for the owner.** If something is not stated, ask. If you must fill a gap to keep a requirement workable, mark it **Derived** or **Open** in the Status column and say so in your reply. Never mark your own assumption as **Owner**.
- **IDs:** each requirement has an ID (customer: `AUTH-`, `ONB-`, `PAY-`, `HOME-`, `CAL-`, `SVC-`, `SKIP-`, `PAUSE-`, `SCHED-`, `SUB-`, `VEH-`, `SUP-`, `ISS-`, `CMP-`, `FDBK-`, `CHK-`, `NOTIF-` and others; admin: `ADM-<area>-NN`; crew: `CRW-<area>-NN`). Never renumber. Add new IDs at the end of their group, even if that puts them out of order in the table.
- **Cross-references:** an ID cited in one file must exist in a file. After any edit, check that every cited ID is defined and no ID is defined twice. A one-line grep over the table rows is enough.
- **Keep the three files consistent.** A change in one often needs a matching change in the others: statuses, notifications, the business-rules list, the data-entities list and the "needed by / covered by" table in the admin file. Update section 13 (open questions) and the deferred list when an item is answered or added.
- **Format:** tables with columns ID, Requirement, Status. Plain, short sentences. English only. Only functional requirements.
- **Dates** in the app are `dd-Mon-yy`, for example `07-Nov-26`. Currency is rupees and prices include GST.
- **Version and sources:** bump the version line at the top of a file when its content changes.

## Domain facts to keep straight

- Services: Cleaning-External (20 min, every day), Cleaning-Internal (20 min, on the interior care day), Deep Spa (2 hours). Each service is a separate job. Deep Spa is not in the plan: it is an add-on that existing customers buy separately, proposing one date and a finish-by time. Scheduling does not wait for its payment in MVP.
- A visit is Completed only when all its jobs are done or skipped.
- Billing cycle is 30 calendar days from the first service date. Payments are manual by UPI (statuses Due, Over due, Initiated, Received). A payment Over due for 7 days makes a subscription Inactive.
- A schedule is frozen once, by 8 PM the day before its first day (a weekly schedule before the week starts). Customers change their schedule until 9 PM the day before. The admin is not bound by the 9 PM rule.
- Ratings are general to the visit and not given to any crew member. No crew member sees a customer's name or mobile number.
- Customers sign in by email: an emailed 6-digit code on first sign-in, then a password. Only customers the admin has created can sign in. Crew sign in with mobile number and password. Admins sign in with a user ID (the first is `priveopapa`) and password. Passwords are never sent by SMS or WhatsApp: the admin sees a new crew password once and hands it over. The admin password comes from `.env`, never from the repo.

## Working conventions

- This project is its own git repo with remote `https://github.com/jazgitt/priveo`. It sits inside the parent `AI3weeks` repo's folder, so run git commands from this folder.
- Nothing is carried over from the user's other projects. Do not assume their tools, hosting or setup. Ask when a choice is needed.
- Commit and push only when the user asks. Never commit `.env` files or secrets.

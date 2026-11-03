# Owner decision, 3 Nov 2026: customers sign in with the mobile number and an MPIN

Recorded from the owner's message of 3 Nov 2026 and the owner's four answers to the questions that followed. Requirement rows: AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-08, AUTH-11 to AUTH-21, ACC-06, ACC-08, ACC-09 (customer file), ADM-CUS-01 to ADM-CUS-04, ADM-CUS-17, ADM-CUS-19 to ADM-CUS-21, ADM-CUS-24, ADM-CUS-30 to ADM-CUS-32 (admin file), CRW-ACC-02, CRW-ACC-10, CRW-ACC-13 (crew file).

## What the owner decided

1. Emails are no longer mandatory, so a customer no longer signs in with the email. They use the mobile number and a 6-digit MPIN, as crew use the mobile number and a password.
2. The mobile number is mandatory for every customer.
3. A customer the admin creates gets a first MPIN: the last 6 digits of the mobile number. At the first sign-in the customer must change it. After that they sign in with their own MPIN and can change it whenever they want.
4. The word "password" becomes "MPIN" wherever a customer sees it. Crew and admin wording does not change.

## The owner's four answers

| Question | Answer |
|---|---|
| How does the app know a 10-digit number is a customer or crew? | The sign-in screen asks which (Customer or Crew), and the request carries the role. |
| What happens to existing customers? | Convert all of them: mobile number and first MPIN, forced change, old passwords stop. |
| How does a customer recover a forgotten MPIN? | The admin resets it to the first MPIN, and the customer must change it again. |
| How is the conversion run? | One-off script, run by hand, never inside a migration or workflow. |

## How it was built (for reference)

- The first MPIN is enforced by the API: until a customer changes it, every customer request except Change MPIN is refused with `mpin_change_required`.
- A login is unique on role plus login ID, so one mobile number can be a customer and a crew member.
- The emailed code for Forgot MPIN still works for a customer with an email saved. A customer with none is told to ask Priveo.
- `scripts/convert_customer_logins.py` does the conversion: a trial run by default, `--apply` to save, the database host printed first, counts only in the report, safe to run again. It skips (and counts) a mobile number two customers share, and one that is not 10 digits.

## Not decided by the owner (marked Derived or Open)

- A customer cannot change their own mobile number in the app (AUTH-21, ACC-06). Derived; the owner can allow it.
- The Customer or Crew choice is shown only for a 10-digit number (AUTH-20). Derived.
- The demo customer's login is the mobile number `9000000001`, and its secret (`MOCK_CUSTOMER_PASSWORD`) must now be 6 digits. Open: the owner sets the value on `test`.

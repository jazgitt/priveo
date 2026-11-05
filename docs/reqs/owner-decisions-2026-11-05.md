# Owner decisions, 05-Nov-26: last name optional and mobile entry

Recorded from the owner's instructions of 5 Nov 2026. Requirements: ONB-01, ONB-02, ACC-06 and the Customer entity (customer file); ADM-CUS-01, ADM-CUS-24, ADM-CRW-02 (admin file).

| # | Decision | Requirement |
|---|---|---|
| 1 | "Make Last name optional everywhere." The last name may be empty when a customer is created or edited in the portal and when the customer fills in onboarding or edits the profile. A last name that is typed must still be letters. Crew have one name field, so nothing changes there. | ONB-01, ONB-02, ACC-06, ADM-CUS-01, ADM-CUS-24 |
| 2 | "Limit max 10 digits in phone number in all input boxes." Mobile number fields take digits only and at most 10 of them (other characters are dropped as they are typed or pasted). Exactly 10 digits are still needed to save. The settings phone values (helpline, seller phone) keep their own rule of 10 to 15 digits with an optional leading +, and the sign-in ID box also takes an email or an admin ID, so neither is capped. | ONB-01, ADM-CUS-01, ADM-CUS-24, ADM-CRW-02 |

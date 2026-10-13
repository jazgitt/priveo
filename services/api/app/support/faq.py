"""The Frequently asked questions (SUP-05).

Priveo supplies the final content later. Until then the list is a Python
constant behind `load_faq()`, so the directory work can swap the body for a
settings document or table without touching the router or the app.
"""
from pydantic import BaseModel


class SupportFaqItem(BaseModel):
    question: str
    answer: str


class SupportFaqOut(BaseModel):
    items: list[SupportFaqItem]


# Placeholder text on the topics named in SUP-05. Replace with Priveo's content.
_FAQ = [
    ("How does billing work?",
     "Your plan renews every 30 days from your first service date. You pay by UPI "
     "and prices include GST. Your invoice appears in billing history once it is ready."),
    ("What happens if I pay late?",
     "A payment that is over due for 7 days makes your subscription Inactive. "
     "Contact Priveo to reactivate it; Priveo sets a new first service date. Payment alone does not restart service."),
    ("How do I skip a visit?",
     "Open Skip or pause from Home and pick the date. A skip must be made by 9 PM "
     "the evening before. A skipped visit is not charged."),
    ("Can I pause my plan?",
     "Yes. Choose a start and end date in Skip or pause. Your renewal date moves "
     "by the days you were paused."),
    ("What is the interior care day?",
     "Once a week the crew also cleans the inside of your car. You can see your "
     "day on Home and in the calendar."),
    ("What if my car is damaged during a clean?",
     "Report an issue from Help, with photos if you have them. We will reply within "
     "4 hours. Damage claims follow Priveo's damage policy."),
    ("Who sees my details?",
     "Crew members never see your name or mobile number. Ratings are given to the "
     "visit as a whole, never to one crew member."),
]


def load_faq() -> list[SupportFaqItem]:
    return [SupportFaqItem(question=q, answer=a) for q, a in _FAQ]

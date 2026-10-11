"""The starting lists, from the customer requirements (FDBK-06, SVC-11, CHK-03).
The admin edits them afterwards (ADM-FDB-06)."""

FEEDBACK_CATEGORIES = [
    ("Exterior finish", "Streaks, dust left, water marks"),
    ("Glass", "Smudges or spots on windshield and windows"),
    ("Wheels and tyres", "Rims not cleaned, tyre dressing missing"),
    ("Interior", "Dashboard, mats, seats, vacuuming (interior days only)"),
    ("Missed spots", "Roof, bumper, door edges"),
    ("Timing", "Car not finished by the service cutoff time"),
    ("Care for the car", "Mirrors folded or unfolded, doors not locked, worry about scratches"),
    ("Area left clean", "Water or cloths left around the parking spot"),
    ("Proof quality", "Photos unclear or missing"),
]

POSITIVE_TAGS = [
    ("Spotless", ""),
    ("On time", ""),
    ("Great tyre finish", ""),
]

# The six owner categories (CHK-03), with the owner's descriptions.
CHECKIN_CATEGORIES = [
    ("Likelihood to recommend",
     "How likely you are to recommend Priveo to neighbours in your society."),
    ("Value for money", "Whether the service is good value at the current price."),
    ("Schedule fit",
     "Whether the service cutoff time and the interior day still work for you."),
    ("Crew professionalism", "Punctuality, behaviour and uniform."),
    ("App and support",
     "Whether the proof of service was useful and issues were resolved quickly."),
    ("Interest in add-ons",
     "Interest in full spa, polish, ceramic coating and car health checks."),
]

# The earlier descriptions of the first three, so the migration can replace
# them without touching text the admin has edited.
OLD_CHECKIN_DESCRIPTIONS = {
    "Likelihood to recommend": "How likely you are to recommend Priveo to your neighbours.",
}

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

CHECKIN_CATEGORIES = [
    ("Likelihood to recommend",
     "How likely you are to recommend Priveo to your neighbours."),
    ("Value for money", "Whether the service is good value at the current price."),
    ("Schedule fit",
     "Whether the service cutoff time and the interior day still work for you."),
]

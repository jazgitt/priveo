"""The starting reference data, from the requirements and from what other
modules hard-coded before the directory existed. `seed_defaults` inserts it
once and never overwrites what the admin has changed."""

SERVICES = ("Cleaning-External", "Cleaning-Internal", "Deep Spa")
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

# ADM-SVS-09: planning durations in minutes.
DURATIONS = {"Cleaning-External": 20, "Cleaning-Internal": 20, "Deep Spa": 120}
# DERIVED. (photos, videos) the crew must upload before "Mark complete"
# (ADM-CHK-06). The owner has not given the numbers.
PROOF_MINIMUMS = {"Cleaning-External": (2, 1), "Cleaning-Internal": (2, 1), "Deep Spa": (2, 1)}

# ADM-SVS-05: (start, end) in minutes after midnight, on every day of the week.
DEFAULT_SLOT_WINDOWS = {
    "Cleaning-External": (5 * 60, 11 * 60),
    "Cleaning-Internal": (5 * 60, 11 * 60),
    "Deep Spa": (0, 1440),
}

# ADM-CHK-07. Cleaning-External is the prototype's list. The other two are
# owner-authorized five-step samples, editable in the portal. (key, label).
CHECKLISTS: dict[str, tuple[tuple[str, str], ...]] = {
    "Cleaning-External": (
        ("body", "Exterior body cleaned"), ("glass", "Glass cleaned"),
        ("wheels", "Wheels cleaned"), ("tyres", "Tyres dressed"),
        ("inspection", "Final inspection completed")),
    "Cleaning-Internal": (
        ("seats", "Seats and mats vacuumed"), ("dashboard", "Dashboard and panels wiped"),
        ("glass", "Interior glass cleaned"), ("touchpoints", "Door handles and touchpoints cleaned"),
        ("inspection", "Final inspection completed")),
    "Deep Spa": (
        ("body", "Exterior body cleaned"), ("vacuum", "Interior vacuumed"),
        ("dashboard", "Dashboard and panels wiped"), ("glass", "Glass and wheels cleaned"),
        ("inspection", "Final inspection completed")),
}

# ADM-CNC-01. (key, label).
REASONS: tuple[tuple[str, str], ...] = (
    ("car_not_in_spot", "Car not in the parking spot"),
    ("car_locked", "Car is locked"),
    ("customer_did_not_allow", "Customer did not allow"),
    ("bad_weather", "Bad weather"),
    ("other", "Other"),
)

# ADM-SET-01, PAY-01, PAY-02: Premium Care is the only plan to start with.
PLAN = {
    "name": "Premium Care", "monthly_price_rupees": 999, "list_price_rupees": 1499,
    "includes_interior": True, "badge": "Founding member",
    "inclusions": [
        "Exterior cleaning 7 days a week",
        "Interior cleaning on your chosen day each week",
        "Weekly tyre dressing and glass treatment",
        "Car Health Check and puncture assistance",
    ],
}

# ADM-ADD-01: Deep Spa is the first add-on. The price is a placeholder until
# the owner confirms it (it matches the earlier MONEY_* default).
ADDON = {
    "name": "Deep Spa", "service": "Deep Spa", "price_rupees": 1500,
    "list_price_rupees": 2000, "duration_minutes": 120,
    "description": "A full interior and exterior spa for your car.",
}

# DERIVED starter list for ADM-REF-03 so the onboarding dropdowns are not
# empty. (make, model, category). Variants are generic placeholders.
CATALOGUE_MODELS = (
    ("Maruti Suzuki", "Swift", "Hatchback"), ("Maruti Suzuki", "Baleno", "Hatchback"),
    ("Maruti Suzuki", "Dzire", "Sedan"), ("Maruti Suzuki", "Brezza", "Compact SUV"),
    ("Maruti Suzuki", "Ertiga", "MUV"), ("Hyundai", "i20", "Hatchback"),
    ("Hyundai", "Venue", "Compact SUV"), ("Hyundai", "Creta", "SUV"),
    ("Tata", "Punch", "Compact SUV"), ("Tata", "Nexon", "Compact SUV"),
    ("Honda", "City", "Sedan"), ("Kia", "Seltos", "SUV"),
    ("Mahindra", "XUV700", "Large SUV"), ("Toyota", "Innova Crysta", "MUV"),
)
CATALOGUE_VARIANTS = ("Base", "Mid", "Top")

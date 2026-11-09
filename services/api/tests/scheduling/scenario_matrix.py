"""The scenario-data matrix: which named scenario or test covers each SCHR- rule.

Three kinds of entry, and every SCHR- row of docs/reqs/scheduler-requirements.md
must appear in exactly one of them (checked by rules_v2/test_scenario_matrix.py):

1. SCENARIO_RULES: a scenario in tests/scheduling/scenarios.py builds the data and
   a test in rules_v2/test_scenario_data.py checks the rules.
2. Tests by name: a test whose name starts with `test_schr_<id>` covers the rule
   (the convention every rules_v2 file already uses). Found by reading the test tree.
3. NOT_PLANNER: a rule the planner does not decide (a screen, a report, an audit
   entry, a seed or a config value). A reason says where it is checked, if anywhere.

KNOWN_OPEN: a rule whose test exists but is an expected failure (open defect).
KNOWN_GAPS: planner rules with no scenario and no test. The coverage test fails if
the set of uncovered planner rules differs from KNOWN_GAPS, so the list cannot grow
or shrink quietly.
"""

SCENARIO_RULES: dict[str, tuple[str, ...]] = {
    "weekly_off_wednesday": ("SCHR-PAR-02", "SCHR-PAR-16", "SCHR-HARD-07"),
    "home_zones_absent_and_zoneless_car": ("SCHR-ZONE-01", "SCHR-ZONE-03", "SCHR-ZONE-06",
                                           "SCHR-ZONE-08"),
    "breaks_site_crew_and_date_range": ("SCHR-PAR-09", "SCHR-BRK-06", "SCHR-BRK-07"),
    "trainee_follows_member": ("SCHR-ZONE-09", "SCHR-HARD-01"),
    "interior_oldest_week_first": ("SCHR-INT-12", "SCHR-INT-02"),
    "weekend_cutoff_is_soft": ("SCHR-WKE-01", "SCHR-WKE-03", "SCHR-WKE-06", "SCHR-PAR-10"),
    "weekday_cutoff_is_hard": ("SCHR-CUT-09", "SCHR-HARD-08"),
    "sick_leave_and_late_start": ("SCHR-HARD-01", "SCHR-HARD-02"),
    "hand_placement_past_cutoff": ("SCHR-HIER-08", "SCHR-CUT-05"),
    "deferred_interior_returns_to_pending": ("SCHR-DEF-03", "SCHR-DEF-01"),
    "exterior_shortfall": ("SCHR-EXT-01", "SCHR-EXT-04", "SCHR-HARD-09", "SCHR-OUT-04"),
    "shift_too_short": ("SCHR-HARD-13", "SCHR-OUT-04"),
}

# Expected failures: the test exists, is marked strict xfail, and names the open defect.
KNOWN_OPEN: dict[str, str] = {
    "SCHR-INT-21": "test_schr_int_21_an_interior_left_unplaced_stays_pending",
}

NOT_PLANNER: dict[str, str] = {
    "SCHR-CFG-02": "Every value editable in the portal: screen",
    "SCHR-CFG-10": "Where new admin sections go: screen decision",
    "SCHR-CUT-06": "Names of the three cutoffs on screens and reports: screen",
    "SCHR-OUT-01": "Daily cleaner view: report and screen",
    "SCHR-OUT-05": "Reports on the Schedule page: screen",
}

KNOWN_GAPS: dict[str, str] = {
    "SCHR-OUT-03": "Exception report content (unassigned Exteriors, pending Interiors, weekend "
                   "lateness): no scenario yet; SCHS-27 tests do not carry this ID",
}

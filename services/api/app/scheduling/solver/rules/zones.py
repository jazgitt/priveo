"""Home zone first, other zones into spare capacity (SCHS-44; SCHR-ZONE-02 to 05,
08, 10, 11, SCHR-EXT-10).

The module reads one per-day input, `ctx.inputs["zones"]`, built by `day_inputs`:

    {"home": {crew key: zone id or None},      # the zone each cleaner fills first
     "vehicle_zone": {vehicle key: zone id},   # cars without a zone are absent
     "owned": [zone ids with a home cleaner],
     "cross_allowed": bool}                    # site.cross_zone_help_allowed

and adds one objective, `zone` (the weight is `scheduler.weight_zone`). It ranks
below placed minutes in the default order, so a cleaner crosses into another zone
only when that places work that would otherwise stay open (ZONE-03), and above the
lateness and early objectives. A hard Customer cutoff stays a hard limit, so a
cross-zone job never pushes a home-zone job past it (ZONE-04). The objective
rewards, from the most to the least important:

* few cross-zone assignments (a job in a zone other than its cleaner's home zone,
  ZONE-10),
* few zones per cleaner beyond the first,
* no overlap between the time spans of two zones of one cleaner, which keeps the
  jobs of a zone together, so the zone switches are the fewest (ZONE-02, EXT-10).

Cars with no zone and cleaners with no home zone take no part (ZONE-08). A day
where no cleaner has a home zone adds nothing (ZONE-11). Movement across zones costs no extra minutes
(ZONE-05): the durations are not changed.

Derived: with `site.cross_zone_help_allowed` off, a cleaner never takes a job of a
zone that has a home cleaner at the site; a zone that nobody owns is still served
(ZONE-07). The three tiers below only rank the parts of this one objective.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scheduling.solver.core import ModelContext, SolverCrew

NAME = "zones"
PRIORITY = 60
CROSS_COST = 10_000  # one cross-zone assignment
ZONE_COST = 100  # one more zone for a cleaner in a day
OVERLAP_COST = 1  # two zones of a cleaner that overlap in time
CROSS_SETTING = "site.cross_zone_help_allowed"
# Derived: a cleaner with no home zone, on a site where some cleaner has one,
# counts as cross-zone for every zoned car (soft cost, never a hard limit).
HOMELESS_IS_CROSS = True


def _cleaner(key: str) -> str:
    """The cleaner behind a window key ("<crew id>|<window>")."""
    return key.split("|", 1)[0]


def day_inputs(run_ctx, day: date, crew: list[SolverCrew]) -> dict | None:
    """Home zones of the day's cleaners and the zone of each car; None when the
    no cleaner of the day has a home zone."""
    if not crew:
        return None
    from sqlalchemy import select

    from app.customers.models import Vehicle
    from app.directory.models import Zone
    from app.scheduling import home_zone
    from app.scheduling.models import SchedulingCrew

    db = run_ctx.db
    rows = {c.id: c for c in db.scalars(select(SchedulingCrew).where(
        SchedulingCrew.society_id == run_ctx.society_id, SchedulingCrew.active.is_(True)))}
    zone_of = {cid: home_zone.effective_zone_id(db, sc) for cid, sc in rows.items()}
    owned = {str(z) for z in zone_of.values() if z is not None}
    home: dict[str, str | None] = {}
    for c in crew:
        zone = zone_of.get(uuid.UUID(c.key.split("|", 1)[0]))
        home[c.key] = str(zone) if zone is not None else None
    if not any(home.values()):
        return None
    cars = {
        str(v): str(z) for v, z in db.execute(
            select(Vehicle.id, Vehicle.zone_id).join(Zone, Zone.id == Vehicle.zone_id)
            .where(Zone.society_id == run_ctx.society_id))}
    data = {
        "home": home, "vehicle_zone": cars, "owned": sorted(owned),
        "cross_allowed": bool(run_ctx.settings.get(CROSS_SETTING, True)),
        "crew": {c.key: (c.start, c.end) for c in crew},
    }
    # The reason step (post_solve/zone_reason.py) reads the same facts.
    if not hasattr(run_ctx, "zone_days"):
        run_ctx.zone_days = {}
    run_ctx.zone_days[day] = data
    return data


def add_day_terms(ctx: ModelContext) -> None:
    data = ctx.inputs.get(NAME)
    if not data:
        return
    model, step = ctx.model, ctx.params.step
    home, cars = data["home"], data["vehicle_zone"]
    owned = set(data.get("owned", ()))
    allowed = data.get("cross_allowed", True)

    # Per cleaner (not per working window, so a split shift counts once):
    # (zone, literal or None for a kept job, start, duration in steps).
    entries: dict[str, list] = {}
    cross = []
    any_home = any(v is not None for v in home.values())
    for job in ctx.free:
        zone = cars.get(job.vehicle)
        if zone is None or job.key not in ctx.placed_vars:
            continue
        for c in ctx.crew:
            lit = ctx.presence.get((job.key, c.key))
            if lit is None:
                continue
            entries.setdefault(_cleaner(c.key), []).append(
                (zone, lit, ctx.start_vars[job.key], ctx.durations[job.key]))
            mine = home.get(c.key)
            if mine is None and any_home and HOMELESS_IS_CROSS:
                # HOMELESS_IS_CROSS (Derived): a cleaner with no home zone takes a
                # zoned car only as cross-zone work, soft, so coverage still wins.
                cross.append(lit)
            elif mine is not None and mine != zone:
                if not allowed and zone in owned:
                    model.Add(lit == 0)
                else:
                    cross.append(lit)
    for job in ctx.kept:
        zone = cars.get(job.vehicle)
        if zone is None or job.fixed is None or job.fixed[0] not in home:
            continue
        start = job.fixed[1] // step
        entries.setdefault(_cleaner(job.fixed[0]), []).append(
            (zone, None, start, -(-job.duration // step)))

    penalty = []
    if cross:
        penalty.append(CROSS_COST * sum(cross))
    horizon = 1440 // step + 1
    for key, items in entries.items():
        zones = sorted({z for z, *_ in items})
        if len(zones) < 2:
            continue
        used, first, last = {}, {}, {}
        for z in zones:
            mine = [e for e in items if e[0] == z]
            u = model.NewBoolVar(f"zu_{key}_{z}")
            lits = [e[1] for e in mine if e[1] is not None]
            if len(lits) < len(mine):
                model.Add(u == 1)  # a kept job of the zone is already there
            else:
                model.AddMaxEquality(u, lits)
            used[z] = u
            first[z] = model.NewIntVar(0, horizon, f"zf_{key}_{z}")
            last[z] = model.NewIntVar(0, horizon, f"zl_{key}_{z}")
            for _z, lit, start, dur in mine:
                lo, hi = first[z] <= start, last[z] >= start + dur
                if lit is None:
                    model.Add(lo)
                    model.Add(hi)
                else:
                    model.Add(lo).OnlyEnforceIf(lit)
                    model.Add(hi).OnlyEnforceIf(lit)
        anyone = model.NewBoolVar(f"zany_{key}")
        model.AddMaxEquality(anyone, list(used.values()))
        penalty.append(ZONE_COST * (sum(used.values()) - anyone))
        for i, a in enumerate(zones):
            for b in zones[i + 1:]:
                a_first, b_first = model.NewBoolVar(f"zab_{key}_{a}_{b}"), model.NewBoolVar(f"zba_{key}_{a}_{b}")
                model.Add(last[a] <= first[b]).OnlyEnforceIf(a_first)
                model.Add(last[b] <= first[a]).OnlyEnforceIf(b_first)
                clash = model.NewBoolVar(f"zov_{key}_{a}_{b}")
                model.AddBoolOr([a_first, b_first, clash, used[a].Not(), used[b].Not()])
                penalty.append(OVERLAP_COST * clash)
    if penalty:
        ctx.add_term("zone", -sum(penalty))

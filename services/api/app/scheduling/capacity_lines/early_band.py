"""The early band, from the first-job time to the Interior-earliest time (05:30
to 07:00 by default). Free minutes in it are shown in capacity as available for
onboarding. The scheduler neither holds them back nor reserves them
(SCHR-EXT-09, Derived; SCHR-EXT-08). Only free minutes are counted: the break
and jobs already scheduled are taken out."""
from app.directory import lookup
from app.directory.site_settings import SettingMissing
from app.scheduling import crew_rules


def _overlap(window: tuple[int, int], band: tuple[int, int]) -> tuple[int, int] | None:
    s, e = max(window[0], band[0]), min(window[1], band[1])
    return (s, e) if e > s else None


def _free(window, band, busy) -> int:
    inside = _overlap(window, band)
    if inside is None:
        return 0
    free = inside[1] - inside[0]
    merged: list[list[int]] = []
    for s, e in sorted(x for x in (_overlap(b, inside) for b in busy) if x):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return free - sum(e - s for s, e in merged)


def day_fields(db, society_id, day, ctx) -> dict:
    try:
        end = int(lookup.site_setting(db, society_id, "site.interior_earliest_minute"))
    except SettingMissing:
        return {}
    total = 0
    for cid, wins in ctx.windows.items():
        start = crew_rules.first_job_minute(db, ctx.crew[cid])
        busy = ctx.busy.get(cid, [])
        total += sum(_free(w, (start, end), busy) for w in wins)
    return {"early_band_free_minutes": total}

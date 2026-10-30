"""The retention job, run by the same protected cron endpoint as the other jobs:
`POST /v1/internal/cron/mani-retention` with `Authorization: Bearer $CRON_SECRET`.

The shared route in `app.notifications.cron` looks a job up by name and checks the secret
first, so the job is added to its table here (a second route on the same path would never
be reached). Scheduling it in `vercel.json` is the coordinator's step, not this file's."""
from datetime import datetime

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.mani.config import get_mani_settings
from app.mani.retention import delete_old_conversations


def _mani_retention(db: Session, now: datetime, _settings) -> dict:
    return {"deleted": delete_old_conversations(db, now, get_mani_settings().conversation_retention_days)}


def register(app: FastAPI) -> None:
    from app.notifications.cron import JOBS

    JOBS["mani-retention"] = _mani_retention

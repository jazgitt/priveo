from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.platform.config import Settings, get_settings

router = APIRouter(prefix="/v1/public", tags=["public"])


class Health(BaseModel):
    status: str
    version: str
    build_number: str


class AppConfig(BaseModel):
    min_app_version: str


@router.get("/health", response_model=Health)
def health(s: Settings = Depends(get_settings)):
    return Health(status="ok", version=s.app_version, build_number=s.build_number)


@router.get("/config", response_model=AppConfig)
def config(s: Settings = Depends(get_settings)):
    return AppConfig(min_app_version=s.min_app_version)

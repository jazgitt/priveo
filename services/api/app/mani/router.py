from fastapi import APIRouter, Depends

from app.identity.service import User
from app.mani.access import require_founder
from app.mani.config import ManiSettings, get_mani_settings
from app.mani.schemas import StatusOut

admin = APIRouter(prefix="/v1/admin/mani", tags=["mani"])


@admin.get("/status", response_model=StatusOut)
def mani_status(_founder: User = Depends(require_founder),
           settings: ManiSettings = Depends(get_mani_settings)) -> StatusOut:
    """Who may use Mani and which model backend is configured. The key is never shown."""
    return StatusOut(backend=settings.backend, chat_model=settings.chat_model,
                     embedding_model=settings.embedding_model)

from fastapi import APIRouter, Depends

from app.home.repository import HomeRepository
from app.home.schemas import AdminHome, CrewHome
from app.identity.service import User
from app.platform.deps import get_home_repository, require_role

crew = APIRouter(prefix="/v1/crew", tags=["crew"])
admin = APIRouter(prefix="/v1/admin", tags=["admin"])


@crew.get("/home", response_model=CrewHome)
def crew_home(user: User = Depends(require_role("crew")),
              repo: HomeRepository = Depends(get_home_repository)):
    # Crew responses never carry a customer name or mobile number.
    return repo.crew_home(str(user.id))


@admin.get("/home", response_model=AdminHome)
def admin_home(user: User = Depends(require_role("admin")),
               repo: HomeRepository = Depends(get_home_repository)):
    return repo.admin_home(str(user.id))

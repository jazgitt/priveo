from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.customers import account, history
from app.customers.service import CustomerService, Onboarding, OnboardingAnswers, OnboardingDraft
from app.home.schemas import CustomerHome
from app.identity.service import User
from app.media.store import ObjectStore, get_object_store
from app.platform.db import get_db
from app.platform.deps import require_role

router = APIRouter(prefix="/v1/customer", tags=["customer"])
router.include_router(account.router)
router.include_router(history.router)


def get_customer_service(db: Session = Depends(get_db),
                         store: ObjectStore = Depends(get_object_store)) -> CustomerService:
    return CustomerService(db, store)


@router.get("/home", response_model=CustomerHome)
def customer_home(user: User = Depends(require_role("customer")),
                  customers: CustomerService = Depends(get_customer_service)):
    return customers.home(user.id)


@router.get("/onboarding", response_model=Onboarding)
def onboarding(user: User = Depends(require_role("customer")),
               customers: CustomerService = Depends(get_customer_service)):
    """The details the admin entered, for the customer to review (ONB-25)."""
    return customers.onboarding(user.id)


@router.post("/onboarding/confirm", status_code=204)
def confirm_onboarding(body: OnboardingAnswers,
                       user: User = Depends(require_role("customer")),
                       customers: CustomerService = Depends(get_customer_service)):
    """Saves the customer's changes and confirms the review. Home opens after it."""
    customers.confirm_onboarding(user.id, body)


@router.patch("/onboarding/draft", status_code=204)
def save_onboarding_draft(body: OnboardingDraft,
                          user: User = Depends(require_role("customer")),
                          customers: CustomerService = Depends(get_customer_service)):
    customers.save_draft(user.id, body)

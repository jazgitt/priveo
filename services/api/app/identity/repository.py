from dataclasses import dataclass
from typing import Protocol

from app.platform.config import Settings


@dataclass(frozen=True)
class User:
    id: str
    role: str  # customer | crew | admin
    display_name: str
    login_id: str
    password: str


class UserRepository(Protocol):
    def find_by_login_id(self, login_id: str) -> User | None: ...
    def get(self, user_id: str) -> User | None: ...


class MockUserRepository:
    def __init__(self, settings: Settings):
        self._users = [
            User("u-customer", "customer", "Aarav Mehta", "customer@priveo.test",
                 settings.mock_customer_password),
            User("u-crew", "crew", "Ravi Kumar", "9000000002", settings.mock_crew_password),
            User("u-admin", "admin", "Priveo Admin", "priveopapa", settings.mock_admin_password),
        ]

    def find_by_login_id(self, login_id: str) -> User | None:
        key = login_id.strip().lower()
        return next((u for u in self._users if u.login_id.lower() == key), None)

    def get(self, user_id: str) -> User | None:
        return next((u for u in self._users if u.id == user_id), None)

from datetime import timedelta
from typing import Protocol

from app.home.schemas import (
    AdminHome,
    CrewHome,
    CustomerHome,
    JobCard,
    NextService,
    PaymentToConfirm,
    QuickAction,
    VehicleCard,
)
from app.platform.clock import today_ist


class HomeRepository(Protocol):
    def customer_home(self, user_id: str) -> CustomerHome: ...
    def crew_home(self, user_id: str) -> CrewHome: ...
    def admin_home(self, user_id: str) -> AdminHome: ...


class MockHomeRepository:
    """Phase 0 mock data. Phase 1 onward replaces this with the database."""

    def customer_home(self, user_id: str) -> CustomerHome:
        return CustomerHome(
            greeting_name="Aarav",
            vehicle=VehicleCard(registration="MH 12 AB 1234", model="Hyundai Creta",
                                society="Green Meadows", parking="B2-14"),
            next_service=NextService(date=today_ist() + timedelta(days=1),
                                     service="Cleaning-External", status="Scheduled"),
            subscription_status="Active",
            quick_actions=[
                QuickAction(key="skip_pause", label="Skip or Pause"),
                QuickAction(key="history", label="Service History"),
                QuickAction(key="feedback", label="Give Feedback"),
                QuickAction(key="report_issue", label="Report an Issue"),
            ],
        )

    def crew_home(self, user_id: str) -> CrewHome:
        jobs = [
            JobCard(id="j1", time="07:00", vehicle="MH 12 AB 1234", parking="B2-14",
                    service="Cleaning-External", status="Done"),
            JobCard(id="j2", time="07:20", vehicle="MH 12 CD 5678", parking="B2-15",
                    service="Cleaning-Internal", status="In progress"),
            JobCard(id="j3", time="07:40", vehicle="MH 14 EF 9012", parking="B1-03",
                    service="Cleaning-External", status="Pending"),
            JobCard(id="j4", time="08:00", vehicle="MH 12 GH 3456", parking="B1-07",
                    service="Deep Spa", status="Pending"),
        ]
        done = sum(1 for j in jobs if j.status == "Done")
        return CrewHome(date=today_ist(), society="Green Meadows", total=len(jobs),
                        done=done, left=len(jobs) - done, jobs=jobs)

    def admin_home(self, user_id: str) -> AdminHome:
        return AdminHome(
            alert_count=3,
            payments_to_confirm=[
                PaymentToConfirm(id="p1", customer_label="Flat A-101", amount_rupees=1499,
                                 reference="UPI 4021"),
                PaymentToConfirm(id="p2", customer_label="Flat C-304", amount_rupees=1499,
                                 reference="UPI 7788"),
            ],
            needs_scheduling_count=2,
        )

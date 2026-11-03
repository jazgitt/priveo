from typing import Protocol

from app.home.schemas import CrewHome, JobCard
from app.platform.clock import today_ist


class HomeRepository(Protocol):
    def crew_home(self, user_id: str) -> CrewHome: ...


class MockHomeRepository:
    """Mock data for the crew home, until its module exists. The customer home
    reads the database (app.customers.service), the admin home too
    (app.home.admin). The parking shows the zone in front, as on the real crew
    job card."""

    def crew_home(self, user_id: str) -> CrewHome:
        jobs = [
            JobCard(id="j1", time="07:00", vehicle="MH 12 AB 1234", parking="Zone 1 · B2-14",
                    service="Cleaning-External", status="Done"),
            JobCard(id="j2", time="07:20", vehicle="MH 12 CD 5678", parking="Zone 1 · B2-15",
                    service="Cleaning-Internal", status="In progress"),
            JobCard(id="j3", time="07:40", vehicle="MH 14 EF 9012", parking="Zone 2 · B1-03",
                    service="Cleaning-External", status="Pending"),
            JobCard(id="j4", time="08:00", vehicle="MH 12 GH 3456", parking="Zone 2 · B1-07",
                    service="Deep Spa", status="Pending"),
        ]
        done = sum(1 for j in jobs if j.status == "Done")
        return CrewHome(date=today_ist(), society="Green Meadows", total=len(jobs),
                        done=done, left=len(jobs) - done, jobs=jobs)

"""Importing this module registers every table with the database metadata."""
from app.crew import models as crew  # noqa: F401
from app.customers import models as customers  # noqa: F401
from app.directory import models as directory  # noqa: F401
from app.identity import models as identity  # noqa: F401

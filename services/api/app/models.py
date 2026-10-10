"""Importing this module registers every table with the database metadata."""
from app.addons import models as addons  # noqa: F401
from app.billing import models as billing  # noqa: F401
from app.changes import models as changes  # noqa: F401
from app.crew import models as crew  # noqa: F401
from app.customers import models as customers  # noqa: F401
from app.directory import models as directory  # noqa: F401
from app.identity import models as identity  # noqa: F401
from app.media import models as media  # noqa: F401
from app.notifications import models as notifications  # noqa: F401
from app.scheduling import models as scheduling  # noqa: F401
from app.support import models as support  # noqa: F401
from app.visits import models as visits  # noqa: F401

"""Write the OpenAPI contract to packages/api-contract/openapi.json."""
import json
import sys
from pathlib import Path

# Import the API of this checkout, not whichever one the virtualenv was installed from.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app

out = Path(__file__).resolve().parents[3] / "packages" / "api-contract" / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
print(f"wrote {out}")

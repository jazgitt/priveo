"""Write the OpenAPI contract to packages/api-contract/openapi.json."""
import json
from pathlib import Path

from app.main import app

out = Path(__file__).resolve().parents[3] / "packages" / "api-contract" / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
print(f"wrote {out}")

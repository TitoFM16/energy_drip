"""Writes the API's OpenAPI schema to a file, for `openapi-typescript` to
generate TypeScript types from (see packages/api-client/package.json).

Deliberately imports the FastAPI `app` object and calls `.openapi()`
directly rather than hitting a live server's `/openapi.json` — building
the schema doesn't touch the database or Redis at all (route registration
and Pydantic model introspection only), so this works with no server
running, no docker stack up, and no environment beyond the package's own
dependencies. That also makes it usable in CI without standing up the app.
"""

import json
from pathlib import Path

from medical_api.main import app

OUTPUT_PATH = (
    Path(__file__).resolve().parents[3] / "packages" / "api-client" / "generated" / "openapi.json"
)


def main() -> None:
    schema = app.openapi()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

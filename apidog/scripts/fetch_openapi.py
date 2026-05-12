"""
Fetch the live OpenAPI spec from the running mock-api and save it to
``apidog/openapi_live.json``.

Why two specs?
- ``openapi.json`` is a hand-curated copy committed to the repo, so Apidog
  can be set up before the server is even running.
- ``openapi_live.json`` is whatever FastAPI currently generates from the
  source. Run this script after changing the API to refresh the canonical
  spec, then diff against the curated copy and re-import into Apidog.

Usage:
    # 1. start the server (apidog/scripts/start_server.bat)
    # 2. in another terminal:
    python apidog/scripts/fetch_openapi.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

URL = "http://localhost:8000/openapi.json"
OUT = Path(__file__).resolve().parent.parent / "openapi_live.json"


def main() -> int:
    print(f"GET {URL}")
    try:
        with urllib.request.urlopen(URL, timeout=5) as resp:
            spec = json.load(resp)
    except urllib.error.URLError as exc:
        print(f"ERROR: could not reach {URL}: {exc}", file=sys.stderr)
        print("Is the mock-api server running?", file=sys.stderr)
        return 1

    OUT.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
    n_paths = len(spec.get("paths", {}))
    n_schemas = len(spec.get("components", {}).get("schemas", {}))
    print(f"Saved {OUT}")
    print(f"  paths   : {n_paths}")
    print(f"  schemas : {n_schemas}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

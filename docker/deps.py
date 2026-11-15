"""Print the runtime dependencies from pyproject.toml, one per line (used by the Dockerfile)."""

import sys
import tomllib

with open(sys.argv[1], "rb") as f:
    print("\n".join(tomllib.load(f)["project"]["dependencies"]))

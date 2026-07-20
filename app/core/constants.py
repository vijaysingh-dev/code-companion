from pathlib import Path

# Project root (the `code-companion/` directory). This file lives at
# app/core/constants.py, so three parents up is the repo root. Import BASE_DIR
# from here everywhere instead of recomputing paths.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

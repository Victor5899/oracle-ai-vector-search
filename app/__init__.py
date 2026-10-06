"""
REST API package for the Oracle AI Vector Search project.

The Phase 1-7 modules in src/ import each other by plain module name, so
src/ is placed on the import path here instead of changing those modules.
"""

import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parent.parent / "src"

if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

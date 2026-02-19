#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


def is_venv_python() -> bool:
    if getattr(sys, "base_prefix", sys.prefix) != sys.prefix:
        return True
    if getattr(sys, "real_prefix", None):
        return True
    if os.getenv("VIRTUAL_ENV"):
        return True
    # For direct interpreter path invocation (.venv/bin/python)
    exe = Path(sys.executable)
    return ".venv" in exe.parts


def enforce_venv() -> None:
    if is_venv_python():
        return
    msg = (
        "This project requires Python execution inside .venv.\n"
        "Use one of:\n"
        "  .venv/bin/python <script>\n"
        "  source .venv/bin/activate && python <script>"
    )
    raise RuntimeError(msg)

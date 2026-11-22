"""Shared console setup for the test scripts.

Every test file here prints something outside ASCII: mathematical symbols in run_all.py,
an em dash or Chinese text in the README-parity checks. On a Windows console the default
code page is cp1252 / cp936, and printing those raises UnicodeEncodeError *after* tests
have already run, so the job fails for a presentation reason instead of a real one. CI's
windows-latest runner hit exactly this.

Importing this module reconfigures stdout/stderr to UTF-8. It is a no-op where the streams
are already UTF-8 or cannot be reconfigured.
"""

from __future__ import annotations

import sys


def use_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


use_utf8_console()
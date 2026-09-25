#!/usr/bin/env python3
"""Claude Code / Codex hook entry point (shim). Logic lives in driftledger/hook.py."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from driftledger.hook import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())

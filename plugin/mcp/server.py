#!/usr/bin/env python3
"""MCP server entry point (shim). Logic lives in driftledger/mcp_server.py."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from driftledger.mcp_server import main  # noqa: E402

if __name__ == "__main__":
    main()

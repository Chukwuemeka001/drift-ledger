#!/usr/bin/env python3
"""Terminal wrapper for the owner (outside the agent): python3 scripts/dl_owner.py <verb> <args…>.
Inside Claude Code, owner commands run in the UserPromptSubmit hook instead; the agent's Bash calls to
this script or to driftledger owner verbs are denied by the PreToolUse hook."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from driftledger.ownercmd import run  # noqa: E402

if __name__ == "__main__":
    print(run(sys.argv[1], " ".join(sys.argv[2:]), os.getcwd()))

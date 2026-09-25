#!/usr/bin/env python3
"""Tier 2c: Claude Opus 5.5 as the main agent. Thin wrapper over the frozen Tier-2 runner (runner.py, unchanged):
registers the model only. Opus runs on the owner's Max plan, so spend is reported as tokens, not dollars."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner  # noqa: E402

runner.MODELS["opus"] = "claude-opus-5-5"
runner.PRICE["opus"] = (0.0, 0.0, 0.0, 0.0)   # plan usage; token counts are reported by score.py

if __name__ == "__main__":
    sys.argv = [sys.argv[0]] + sys.argv[1:]
    runner.main()

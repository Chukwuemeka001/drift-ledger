"""Owner command parsing/execution shared by the Claude Code prompt hook and the terminal wrapper.

Authority lives in the CALLER: in Claude Code, only the UserPromptSubmit hook calls this, and that hook
fires only for text the owner typed (never for model tool calls). Command files contain nothing executable.

Syntax: /drift-ledger:<verb> <args>
  decide|forbid|park|owe|boundary|mission <text> [| reason: <why>] [| scope: <scope>]
  except <parent-id> <text> [| scope: <scope>]      confirm [ids…]      reject <id>
  discharge <id> [evidence note]    consume <id>    supersede <id> [scope]
  ledger | status | off | on | thread new|use|list [name]
"""
from __future__ import annotations

import io
import re
from contextlib import redirect_stderr, redirect_stdout

from .cli import main as cli

RECORD_VERBS = ("decide", "forbid", "park", "owe", "boundary", "mission")
PREFIX = re.compile(r"^\s*/drift-ledger:([a-z]+)\b\s*(.*)$", re.S)


def parse_prompt(prompt: str):
    m = PREFIX.match(prompt or "")
    return (m.group(1), m.group(2).strip()) if m else (None, None)


def split_fields(s):
    parts = [p.strip() for p in s.split("|")]
    text, extra = parts[0], {}
    for p in parts[1:]:
        k, _, v = p.partition(":")
        if k.strip().lower() in ("reason", "scope") and v.strip():
            extra[k.strip().lower()] = v.strip()
    return text, extra


def to_argv(verb, args):
    a = args.strip()
    if verb in RECORD_VERBS:
        text, ex = split_fields(a)
        if not text:
            raise ValueError(f"usage: /drift-ledger:{verb} <text> [| reason: …] [| scope: …]")
        return [verb, text] + sum(([f"--{k}", v] for k, v in ex.items()), [])
    if verb == "except":
        parent, _, rest = a.partition(" ")
        text, ex = split_fields(rest)
        return ["except", parent, text] + (["--scope", ex["scope"]] if "scope" in ex else [])
    if verb == "confirm":
        toks = [x.strip(",") for x in a.split() if x.lower() != "all"]
        if "as" in toks:                       # /drift-ledger:confirm L5 as obligation
            i = toks.index("as"); return ["confirm"] + toks[:i] + ["--as", toks[i + 1] if i + 1 < len(toks) else ""]
        return ["confirm"] + toks
    if verb in ("reject", "consume"):
        return [verb, a.split()[0]]
    if verb == "discharge":
        i, _, note = a.partition(" ")
        return ["discharge", i] + (["--note", note] if note else [])
    if verb == "supersede":
        i, _, scope = a.partition(" ")
        return ["supersede", i] + (["--scope", scope] if scope else [])
    if verb == "ledger":
        return ["show"]
    if verb in ("off", "on", "status"):
        return [verb]
    if verb == "thread":
        return ["thread"] + a.split()[:2]
    raise ValueError(f"unknown Drift Ledger command '{verb}'")


def run(verb, args, cwd, session_id=None) -> str:
    try:
        argv = ["--cwd", cwd] + (["--session", session_id] if session_id else []) + to_argv(verb, args)
    except (ValueError, IndexError) as ex:
        return f"Drift Ledger: {ex}"
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        cli(argv)
    return (out.getvalue() + err.getvalue()).strip() or f"ok ({verb})"

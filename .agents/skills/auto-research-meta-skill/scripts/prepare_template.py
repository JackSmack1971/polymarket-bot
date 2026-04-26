#!/usr/bin/env python3
# prepare.py — IMMUTABLE EVAL HARNESS TEMPLATE
#
# INSTRUCTIONS FOR USER:
#   1. Copy this file to your improvement folder as prepare.py
#   2. Fill in ALL sections marked with # <<< USER FILLS THIS >>>
#   3. chmod 444 prepare.py     ← lock it before launching the loop
#   4. NEVER edit this file after locking. The loop depends on it being stable.
#
# The auto-research loop calls: python prepare.py
# It expects: results/latest_run.json  (written by this script)
#
# ─────────────────────────────────────────────────────────────────────────────

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

SKILL_FILE = "skill.md"          # Do not change — always skill.md
RESULTS_DIR = Path("results")
RUNS_DIR = Path("runs")
HISTORY_FILE = RUNS_DIR / "full_history.jsonl"

# <<< USER FILLS THIS >>>
# Model to use when generating outputs from the skill prompt.
# Examples: "claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"
MODEL = "claude-sonnet-4-6"

# <<< USER FILLS THIS >>>
# How many outputs to generate per test case (1 is fine for deterministic skills;
# use 3 for probabilistic/creative skills to get reliable signal).
SAMPLES_PER_CASE = 1

# ─── LOAD SKILL PROMPT ────────────────────────────────────────────────────────

def load_skill_prompt() -> str:
    with open(SKILL_FILE, "r") as f:
        return f.read()

# ─── TEST CASES ───────────────────────────────────────────────────────────────
#
# <<< USER FILLS THIS >>>
# Define 20–100 test case inputs. These are the inputs your skill will receive.
# Each entry is a dict with at minimum an "input" key.
# You can add "context" for multi-turn setups, "metadata" for grouping, etc.
#
# Example for a LinkedIn writing skill:
#   TEST_CASES = [
#       {"input": "Write a post about shipping a new feature after 6 months of work."},
#       {"input": "Write a post about dealing with imposter syndrome as a senior engineer."},
#       ...
#   ]
#
# Example for a code review skill:
#   TEST_CASES = [
#       {"input": "Review this Python function:\ndef add(a, b):\n  return a+b"},
#       ...
#   ]

TEST_CASES = [
    # <<< USER FILLS THIS >>>
    # {"input": "..."},
    # {"input": "..."},
]

# ─── MODEL CALL ───────────────────────────────────────────────────────────────
#
# <<< USER FILLS THIS >>>
# Implement this function to call your model with the skill as system prompt.
# The loop will call this for every test case.
#
# Using the Claude CLI (simplest approach):
#   result = subprocess.run(
#       ["claude", "-p", user_input, "--system", skill_prompt, "--model", MODEL],
#       capture_output=True, text=True, timeout=60
#   )
#   return result.stdout.strip()
#
# Using the Anthropic Python SDK:
#   import anthropic
#   client = anthropic.Anthropic()
#   msg = client.messages.create(
#       model=MODEL,
#       max_tokens=1024,
#       system=skill_prompt,
#       messages=[{"role": "user", "content": user_input}]
#   )
#   return msg.content[0].text

def call_model(skill_prompt: str, user_input: str) -> str:
    """Call the model with skill_prompt as system, user_input as user message."""
    # <<< USER FILLS THIS >>>
    raise NotImplementedError(
        "Implement call_model() — see comments above for examples."
    )

# ─── BINARY ASSERTIONS ────────────────────────────────────────────────────────
#
# <<< USER FILLS THIS >>>
# Define 20–100 binary assertions. Each MUST return True (pass) or False (fail).
# No scores. No "pretty good". Binary only.
#
# Each assertion is a dict:
#   {
#     "id":   short_snake_case string (used in commit messages and reports),
#     "desc": human-readable description of what PASSING means,
#     "fn":   lambda output: bool
#   }
#
# GOOD assertion examples:
#   {"id": "no_emdash",       "desc": "No em-dashes",          "fn": lambda x: "—" not in x and " -- " not in x},
#   {"id": "ends_declarative","desc": "Never ends with '?'",   "fn": lambda x: not x.strip().endswith("?")},
#   {"id": "under_200_words", "desc": "Under 200 words",       "fn": lambda x: len(x.split()) < 200},
#   {"id": "has_hook",        "desc": "First line ≤12 words",  "fn": lambda x: len(x.split("\n")[0].split()) <= 12},
#   {"id": "no_filler_sorry", "desc": "No 'I apologize'",      "fn": lambda x: "i apologize" not in x.lower()},
#
# BAD assertion examples (do NOT do these):
#   {"fn": lambda x: rate_quality(x) > 7}     ← not binary
#   {"fn": lambda x: "good" in x.lower()}      ← too vague / gameable
#   {"fn": lambda x: len(x) > 50}             ← too easy to satisfy trivially

ASSERTIONS = [
    # <<< USER FILLS THIS >>>
    # {"id": "example_assertion", "desc": "Output is non-empty", "fn": lambda x: len(x.strip()) > 0},
]

# ─── EVALUATION ENGINE ────────────────────────────────────────────────────────
# Do not edit below this line unless you are intentionally changing eval mechanics.

def generate_outputs(skill_prompt: str) -> list[dict]:
    """Run all test cases through the model. Returns list of {input, output}."""
    results = []
    for i, case in enumerate(TEST_CASES):
        user_input = case["input"]
        for _ in range(SAMPLES_PER_CASE):
            try:
                output = call_model(skill_prompt, user_input)
                results.append({"input": user_input, "output": output, "case_index": i})
            except Exception as e:
                print(f"  [WARN] Model call failed for case {i}: {e}", file=sys.stderr)
                results.append({"input": user_input, "output": "", "case_index": i, "error": str(e)})
    return results

def evaluate_outputs(outputs: list[dict]) -> dict:
    """Run all assertions over all outputs. Returns structured report."""
    if not ASSERTIONS:
        raise ValueError("ASSERTIONS list is empty. Fill in at least 20 binary assertions.")
    if not TEST_CASES:
        raise ValueError("TEST_CASES list is empty. Fill in at least 20 test cases.")

    assertion_results: dict[str, dict] = {
        a["id"]: {"id": a["id"], "description": a["desc"], "pass": 0, "fail": 0, "examples": []}
        for a in ASSERTIONS
    }

    total_checks = 0
    total_passed = 0

    for item in outputs:
        out = item.get("output", "")
        for a in ASSERTIONS:
            try:
                passed = bool(a["fn"](out))
            except Exception:
                passed = False
            total_checks += 1
            if passed:
                total_passed += 1
                assertion_results[a["id"]]["pass"] += 1
            else:
                assertion_results[a["id"]]["fail"] += 1
                if len(assertion_results[a["id"]]["examples"]) < 3:
                    assertion_results[a["id"]]["examples"].append(out[:200])

    overall_pass_rate = round(total_passed / total_checks, 4) if total_checks else 0.0

    failing = [
        {
            "id": v["id"],
            "description": v["description"],
            "fail_count": v["fail"],
            "examples": v["examples"],
        }
        for v in sorted(assertion_results.values(), key=lambda x: -x["fail"])
        if v["fail"] > 0
    ]

    # Load last 3 commits for history_summary
    try:
        log = subprocess.run(
            ["git", "log", "--oneline", "-3"], capture_output=True, text=True
        ).stdout.strip()
    except Exception:
        log = ""

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_pass_rate": overall_pass_rate,
        "total_tests": total_checks,
        "passed": total_passed,
        "failing_assertions": failing,
        "history_summary": log,
    }

def write_results(report: dict) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    RUNS_DIR.mkdir(exist_ok=True)

    # Write latest_run.json (overwrite every cycle)
    latest = RESULTS_DIR / "latest_run.json"
    with open(latest, "w") as f:
        json.dump(report, f, indent=2)

    # Append to full_history.jsonl
    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps(report) + "\n")

def main():
    print(f"[auto-research] Loading skill from {SKILL_FILE}...", flush=True)
    skill_prompt = load_skill_prompt()

    print(f"[auto-research] Running {len(TEST_CASES)} test cases × {SAMPLES_PER_CASE} sample(s) × {len(ASSERTIONS)} assertions...", flush=True)
    outputs = generate_outputs(skill_prompt)

    report = evaluate_outputs(outputs)
    write_results(report)

    rate = report["overall_pass_rate"]
    passed = report["passed"]
    total = report["total_tests"]
    fails = len(report["failing_assertions"])
    print(f"Pass rate: {rate*100:.1f}% ({passed}/{total}) | Failing assertion types: {fails}", flush=True)

    # Exit code: 0 = ran successfully (even if pass rate is low)
    # The loop reads results/latest_run.json — exit code is not the signal.
    sys.exit(0)

# ─── GUARDRAIL HELPERS (v3.0) ────────────────────────────────────────────────
# Use these in your ASSERTIONS to ensure compliance with global rules.

def check_gemini_compliance(code: str) -> bool:
    """Check if code follows GEMINI.md rules (e.g. threading locks)."""
    # Example: Ensure threading.Lock() is used if state is updated
    if "state[" in code and "Lock()" not in code:
        return False
    # Example: Ensure daemon=True is used
    if "threading.Thread" in code and "daemon=True" not in code:
        return False
    return True

def check_backend_guardrails(code: str) -> bool:
    """Check if code follows backend-guardrails.md (e.g. Zod, Sentry)."""
    # Example: Ensure Zod is used for validation
    if ".parse(" not in code and ".safeParse(" not in code:
        return False
    return True

if __name__ == "__main__":
    # Phase 0: Rule Ingestion (Pre-flight check)
    if os.path.exists("GEMINI.md"):
        print("[auto-research] Phase 0: Ingested GEMINI.md")
    if os.path.exists("backend-guardrails.md"):
        print("[auto-research] Phase 0: Ingested backend-guardrails.md")
    
    main()

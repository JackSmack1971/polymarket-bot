# Loop Protocol Reference
Auto-Research Meta-Skill — Detailed Mechanics

---

## Table of Contents
1. [latest_run.json Schema](#1-latest_runjson-schema)
2. [Full Decision Matrix](#2-full-decision-matrix)
3. [failures.log Format](#3-failureslog-format)
4. [full_history.jsonl Schema](#4-full_historyjsonl-schema)
5. [Hypothesis Rotation Strategy](#5-hypothesis-rotation-strategy)
6. [Final Report Format](#6-final-report-format)
7. [Edge Case Handling](#7-edge-case-handling)

---

## 1. `latest_run.json` Schema

`prepare.py` MUST produce this exact schema. If it doesn't, the loop cannot proceed.

```json
{
  "timestamp": "2026-04-26T03:14:00.000Z",
  "overall_pass_rate": 0.72,
  "total_tests": 87,
  "passed": 63,
  "failing_assertions": [
    {
      "id": "ends_declarative",
      "description": "Response never ends with a question mark",
      "fail_count": 14,
      "examples": [
        "...so what do you think?",
        "...does this resonate with you?"
      ]
    },
    {
      "id": "no_emdash",
      "description": "No em-dashes in output",
      "fail_count": 8,
      "examples": ["Great results — really outstanding"]
    }
  ],
  "history_summary": "Last 3: +2.1% (ends_declarative), -0.0% reverted, +1.8% (no_emdash)"
}
```

**Required fields:** `timestamp`, `overall_pass_rate`, `total_tests`, `passed`, `failing_assertions`
**Failing assertion required fields:** `id`, `description`, `fail_count`
**Optional but strongly recommended:** `examples` (max 5 per assertion), `history_summary`

---

## 2. Full Decision Matrix

```
AFTER RE-EVALUATION:

pass_rate >= TARGET_PASS_RATE
    → emit final report to results/final_report.md
    → git add skill.md
    → git commit -m "Auto-Research SUCCESS: $(pass_rate)% | Target: $(TARGET_PASS_RATE)%"
    → EXIT LOOP

pass_rate > previous_best_pass_rate (new all-time high, even if < target)
    → git add skill.md
    → git commit -m "Auto-Research #N: +$(delta)% ATH | Fixed: [assertion_id]"
    → update previous_best in memory
    → CONTINUE

pass_rate improved >= 1.5% (but not ATH)
    → git add skill.md
    → git commit -m "Auto-Research #N: +$(delta)% | Fixed: [assertion_id]"
    → CONTINUE

pass_rate improved < 1.5% (marginal gain, not worth commit noise)
    → git add skill.md
    → git commit -m "Auto-Research #N: +$(delta)% (minor) | Fixed: [assertion_id]"
    → CONTINUE
    NOTE: still commit marginal gains — compound improvements matter

pass_rate unchanged (0.0% delta)
    → git reset --hard HEAD
    → log: runs/failures.log (see §3)
    → HYPOTHESIS ROTATION (see §5)
    → CONTINUE

pass_rate decreased (regression)
    → git reset --hard HEAD
    → log: runs/failures.log with regression delta
    → HYPOTHESIS ROTATION (see §5)
    → CONTINUE
```

---

## 3. `failures.log` Format

Append one entry per failed hypothesis. Do not truncate.

```
---
iteration: 12
timestamp: 2026-04-26T04:22:00Z
assertion_targeted: ends_declarative
hypothesis: "Add after line 31: 'End every response with a strong call to action.'"
patch_applied: |
  + End every response with a strong call to action.
result: -1.2% regression (new failures in: brevity_under_150_words)
root_cause: Adding "call to action" directive caused longer responses, breaking brevity assertions.
next_angle: Target ends_declarative without touching response length. Try negative phrasing: "Never end with a question."
---
```

---

## 4. `full_history.jsonl` Schema

One JSON object per line. Append after every cycle (success or failure).

```json
{"iteration": 12, "timestamp": "...", "pass_rate_before": 0.70, "pass_rate_after": 0.68, "delta": -0.02, "assertion_targeted": "ends_declarative", "patch": "...", "committed": false, "revert_reason": "regression: -1.2%"}
{"iteration": 13, "timestamp": "...", "pass_rate_before": 0.70, "pass_rate_after": 0.724, "delta": 0.024, "assertion_targeted": "ends_declarative", "patch": "...", "committed": true, "commit_hash": "a3f9c21"}
```

---

## 5. Hypothesis Rotation Strategy

When a hypothesis fails 2+ consecutive times on the same assertion, rotate angle:

**Rotation ladder (try in order):**
1. **Negative phrasing** — "Never do X" instead of "Always do Y"
2. **Explicit example** — Add a do/don't example directly to skill.md
3. **Structural location** — Move the rule to a more prominent section (top of file, under a `## CRITICAL RULES` header)
4. **Rule decomposition** — Break the failing assertion into two simpler sub-rules
5. **Assertion skip** — If 5+ consecutive hypotheses fail on the same assertion with no progress, log it as "resistant" and move to the next highest-impact failing assertion. Revisit later.

**Never:**
- Repeat the exact same patch that already failed
- Make two changes in the same patch to "fix two things at once"
- Rewrite sections larger than 10 lines

---

## 6. Final Report Format

Emit to `results/final_report.md` on success or graceful stop:

```markdown
# Auto-Research Final Report

**Target skill:** skill.md
**Iterations run:** 42
**Duration:** 6h 14m
**Baseline pass rate:** 48.3%
**Final pass rate:** 96.1%
**Target pass rate:** 95.0%
**Status:** SUCCESS ✓

## Assertion Improvement Summary

| Assertion ID | Baseline | Final | Cycles to Fix |
|---|---|---|---|
| ends_declarative | 38% | 98% | 7 |
| no_emdash | 61% | 100% | 3 |
| brevity_under_150 | 44% | 91% | 12 |

## Key Patches Applied (top 5 by impact)

1. **+4.1%** — Iteration 7: Added "Never end with a question mark" to hard constraints
2. **+3.8%** — Iteration 3: Replaced em-dash rule with explicit negative example
...

## Resistant Assertions (never resolved)
- `tone_warmth`: 14 attempts, max improvement +1.1%. Likely requires test case revision.

## Commit Log
git log --oneline (last 10 commits shown)
```

---

## 7. Edge Case Handling

| Situation | Action |
|---|---|
| `prepare.py` exits non-zero (crash) | Log traceback to `runs/harness_errors.log`, restore `skill.md` with `git checkout skill.md`, skip iteration, continue |
| `results/latest_run.json` not written | Treat as harness crash (above) |
| Git merge conflict on reset | `git reset --hard HEAD && git clean -fd`, continue |
| `skill.md` becomes unparseable/empty | `git checkout HEAD skill.md`, log to `failures.log`, continue |
| MAX_ITER reached without hitting target | Emit final report with status "MAX_ITER_REACHED", exit gracefully |
| `prepare.py` produces 0 failing assertions at baseline | Confirm pass rate ≥ TARGET, emit success report, exit |
| Disk full | Log error, emit partial final report, exit |

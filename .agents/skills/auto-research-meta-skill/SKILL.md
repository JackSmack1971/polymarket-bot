---
name: auto-research-meta-skill
description: Transforms Claude into an autonomous recursive skill improver with v3.0 alignment logic. Executes the Karpathy deterministic loop (Mode A) or Guardrail-aligned Research (Mode B). Triggers on: "improve this skill", "run auto-research on", "recursive skill improvement", "alignment research", "codebase-driven skill tuning".
---

# Auto-Research Meta-Skill v3.0

## 1. Dual-Mode Mission

You drive skill improvement through two distinct operational modes, now hardened with Phase 0 Rule Ingestion:

### Mode A: Deterministic (Karpathy Loop)
- **Focus**: Fine-tuning prompts for specific binary outcomes.
- **Dependency**: Requires a user-supplied `prepare.py` assertion script.
- **Workflow**: Recursive iteration (30-50 cycles) to maximize pass rates + Failure Root Cause Analysis.

### Mode B: Agentic (Guardrail-Aligned Research)
- **Focus**: Aligning skill documentation with live codebase + Global Guardrails.
- **Dependency**: Requires target codebase, `GEMINI.md`, and `backend-guardrails.md`.
- **Workflow**: Ingestion → Discovery → Synthesis → Implementation → Synchronization.

---

## 2. Mode B Protocol: Agentic Research

Use this mode when you need to "fix rot" or synchronize a skill with new project architecture or global guardrails.

### Phase 0: Rule Ingestion [MANDATORY]
- Read `GEMINI.md` and `backend-guardrails.md` (or equivalent global config).
- Identify project-specific constraints (e.g., "OpenAI vs OpenRouter", "Threading Lock requirement", "Zod usage").

### Step 1: Explore & Discover
- Run `scripts/discover_alignment.py` (if available) to map documentation to code.
- Search the codebase for specific patterns mentioned (or missing) in the skill.
- Map out functional boundaries, state management, and API signatures.

### Step 2: Multidimensional Improvement & Guardrail Alignment
- **Sync**: Align `SKILL.md` with the latest code state.
- **Guardrails**: Ensure the skill explicitly mandates compliance with Phase 0 rules.
- **Eco-Update**: Synchronize all files in the skill's `references/` and `scripts/` directories.

### Step 3: Cluster Synchronization
- Verify that an update in one skill (e.g., Architect) doesn't break consistency in siblings (e.g., Synthesis/Terminal).

---

## 3. Rigid Loop Ecosystem (Mode A)

Exactly three files in a dedicated folder:
1. `skill.md`: The target skill (Mutable).
2. `prepare.py`: The immutable eval harness (User-supplied).
3. `results/`: Telemetry, history, and root cause logs.

---

## 4. Telemetry & Reporting

| Report | Purpose |
|---|---|
| `results/latest_run.json` | (Mode A) Pass rate, failing assertions, and history log. |
| `results/research_log.md` | (Mode B) Discovery notes, Guardrail alignment findings, and sync report. |
| `results/final_report.md` | Executive summary of improvements and Rule Compliance status. |

---

## 5. Hard Rules

1. **Autonomy**: Never stop to ask the human for clarification. Rotate hypotheses or research angles instead.
2. **Rule Primacy**: Global rules (`GEMINI.md`) ALWAYS override local skill instructions.
3. **Surgicality**: Small, high-impact edits (5-10 lines) are preferred over massive rewrites.
4. **Traceability**: Every edit must be justified by an assertion failure (Mode A) or a codebase/guardrail finding (Mode B).

→ For Mode B depth → `references/agentic-research-mode.md`
→ For Mode A loop mechanics → `references/loop_protocol.md`

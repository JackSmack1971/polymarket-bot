# Agentic Research Mode (Mode B)

## Overview

Agentic Research is the process of using autonomous reasoning to align a skill's documentation with the ground truth of a codebase and global project guardrails. This version (v3.0) adds a mandatory Rule Ingestion phase to ensure compliance with top-level repository constraints.

---

## The 5-Phase Workflow

### Phase 0: Rule Ingestion [MANDATORY]
Before any research, you must ingest the "Ground Truth" of the repository:
- **Global Rules**: Read `GEMINI.md`, `backend-guardrails.md`, and `.clauderc`.
- **Constraint Mapping**: Identify mandatory patterns (e.g., "Must use `threading.Lock()` for state writes", "Must use `Zod` for validation").
- **Library Check**: If the codebase uses specific libraries (e.g., `pino`, `Sentry`, `Prisma`), use `Context7` to fetch current docs.

### Phase 1: Codebase Discovery
Use exploratory tools to verify every technical claim in the skill.
- **Verification**: `grep_search` for every regex, constant, and function name.
- **Context**: `list_dir` to understand the project structure and identifying missing files.
- **Deep Dive**: `view_file` to read core logic (e.g., main loops, API parsers).

### Phase 2: Synthesis & Guardrail Alignment
Group findings into logical improvements.
- **Patterns**: Identify repeated logic that isn't captured.
- **Compliance**: Audit the skill against Phase 0 rules. If the skill says "use print()", but `backend-guardrails.md` says "use pino", the guardrail wins.
- **Sync**: Identify other skills in the repository that share the same data sources or logic.

### Phase 3: Multidimensional Implementation
Implement improvements across the entire skill ecosystem.
1. **SKILL.md**: Update the high-level rules and mission.
2. **References**: Update or create files in the `references/` folder.
3. **Scripts**: Update or create validation or helper scripts in the `scripts/` folder.

### Phase 4: Alignment Verification
Final check of the "New Skill" vs "Current Code + Guardrails."
- Perform a final `grep_search` to ensure the updated documentation matches the actual code state.
- Create a `results/research_log.md` detailing the alignment findings and Rule Compliance status.

---

## Best Practices

- **Rule Primacy**: If a skill instruction conflicts with a global guardrail, you must fix the skill.
- **Avoid Assumptions**: If a skill says "uses Model X," verify it in the code.
- **Document the 'Why'**: In the `research_log.md`, explain *why* a pattern was added (e.g., "Aligned with backend-guardrails.md: added Zod validation to all API routes").
- **Cluster Awareness**: When improving one skill, check if its "siblings" need the same update.

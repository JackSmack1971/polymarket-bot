# Loop Protocol Reference (v3.0)

## Decision Matrix Integration

### Mode A (Deterministic)
Follow the Karpathy loop using `prepare.py` results.
- **Pass rate improvement** → Commit & Continue.
- **Regression** → Revert & Rotate Hypothesis.
- **Failure Analysis** → Group failures by type (e.g., "Formatting", "Logic", "Constraint") and generate targeted fixes.

### Mode B (Agentic)
Follow the Discovery-Implementation loop.
- **Phase 0 Ingestion** → Load `GEMINI.md` and `backend-guardrails.md`.
- **Alignment Discovery** → Document in `research_log.md`.
- **Guardrail Conflict** → Global rule OVERRIDES local skill (Phase 2).
- **Cluster Inconsistency** → Synchronize sibling skills.
- **Verification** → Internal reasoning vs codebase + Final Grep.

---

## Telemetry Expansion

### `results/research_log.md` (Mode B Only)
Required for tracking agentic discovery and rule compliance.

```markdown
# Agentic Research Log

## Phase 0: Rule Compliance Audit
- Rule: [GEMINI.md] Threading Lock requirement → [PASS/FAIL]
- Rule: [backend-guardrails.md] Zod validation → [PASS/FAIL]

## Discovery Phase
- Found: Event IDs 37049, 36060 are hardcoded in poly_ui.py.
- Found: `updating = False` bug in multiple threads.

## Implementation Phase
- Updated SKILL.md with explicit Event ID registry and Lock requirement.
- Synchronized regex across Synthesis and Terminal skills.

## Verification
- Verified: All documented patterns now align with `poly_ui.py` (v1.2.0) and global guardrails.
```

---

## Final Report Expansion

The `results/final_report.md` should now include a **Rule Compliance** status:

```markdown
# Auto-Research Final Report

**Target skill:** polymarket-bot-architect
**Mode:** B (Agentic Research)
**Status:** SUCCESS ✓
**Alignment Score:** 100%
**Rule Compliance:** FULLY COMPLIANT (Aligned with GEMINI.md v2.1)

## Key Discoveries & Improvements
1. **Thread Safety**: Aligned with GEMINI.md; implemented Lock pattern in docs.
2. **Multi-Event Logic**: Documented the synthesis of 3 separate events.
...
```

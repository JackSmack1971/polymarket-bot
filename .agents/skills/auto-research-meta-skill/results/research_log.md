# Research Log - Polymarket BTC Terminal Alignment

**Date**: 2026-04-26
**Target Skill**: `polymarket-btc-terminal`
**Mode**: B (Agentic Research)

## Phase 0: Rule Ingestion
- **GEMINI.md**: Found requirements for `threading.Lock()`, specific async `updating` flag placement, and history slicing.
- **Backend Guardrails**: Not applicable (Python TUI, not Node backend), but followed Pythonic threading standards.

## Step 1: Explore & Discover
- **Keyword Discovery**: Ran `discover_alignment.py`. 
  - Found 6/7 matches. 
  - `KEY_RESIZE` is MISSING from code but documented in skill.
- **Code Audit (`poly_ui.py`, `poly_or.py`)**:
  - Found `ai_state['updating'] = False` incorrectly placed in the main loop after `thread.start()`.
  - Confirmed total absence of `threading.Lock()` for state dict writes.
  - Confirmed regex `r'\$([0-9,]+)'` is used correctly.

## Step 2: Synthesis & Improvement Proposals
- **Sync Needed**: Move `updating = False` to `finally` blocks in async threads.
- **Guardrail Alignment**: Implement `threading.Lock()` as requested by `GEMINI.md`.
- **Documentation**: Update `SKILL.md` to remove/fix the `KEY_RESIZE` mention and add "Locking" as a non-negotiable.

## Step 3: Cluster Synchronization
- Checked `polymarket-bot-architect` (sibling skill). It also needs alignment on locks (to be handled in a separate run or as part of this cluster update).

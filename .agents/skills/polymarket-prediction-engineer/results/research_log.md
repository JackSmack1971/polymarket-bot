# Research Log - Polymarket Prediction Engineer Improvement

## Phase 0: Rule Ingestion
- **GEMINI.md**: 
    - Sole dependency: `openai`.
    - Threading: `daemon=True`, state dict with `updating` flag.
    - AI Format: `Implied price: $XXX,XXX - [ONE insight ≤100 chars]`.
    - History: Sliced to `[-16:]`.
    - Lock requirement: Wrap all state dict writes in `threading.Lock()`.
- **Backend Guardrails**: 
    - Focus on R-C-S-R and BFRI. (Note: Project is Python curses, so R-C-S-R is applied conceptually to data/logic separation).

## Step 1: Discovery & Alignment
### Discrepancies Found:
1. **Model IDs**: `poly_or.py` uses `moonshotai/kimi-k2`. Skill says `kimi-k2`.
2. **Function Signatures**: `Function Reference` documentation is outdated.
    - Reference says `update_ai_analysis_async(state, loop)`.
    - Code uses `update_ai_analysis_async(current_data, previous_data, ai_state, lock)`.
3. **State Management**: Reference suggests a monolithic `state` dict. Code uses split `ai_state`, `market_state`, `btc_state`.
4. **Line Numbers**: `Model Swap Guide` mentions line ~310. Actual code is ~455.
5. **Alpha Tuning**: `ai-system-architecture.md` contains detailed α-tuning (Momentum/Regime Change) that isn't fully reflected in the main `SKILL.md` Core Invariants.

### Alignment Opportunities:
- Explicitly mandate the use of `threading.Lock()` for all state updates in the skill.
- Synchronize the "Anchor Rule" with the full α-tuning table.
- Include the specific Event IDs (36060, 37057) used for granular data analysis.

## Step 2: Synthesis & Synchronization
- Update `SKILL.md` to reflect the multi-mode α-tuning and precise model names.
- Update `references/function-reference.md` to match the actual Python signatures.
- Update `references/model-swap-guide.md` with correct line ranges.
- Ensure all references mention the `threading.Lock()` requirement.

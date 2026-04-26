---
name: polymarket-btc-synthesis
description: Polymarket Gamma/CLOB API expert for multi-event Bitcoin prediction synthesis. Use when the user mentions Polymarket, Gamma API, CLOB, event IDs (37049, 36060, 37057), implied Bitcoin price, fetch_event_markets, calculate_implied_bitcoin_price, fine ranges, broad ranges, reach/dip markets, poly_ui.py, poly_or.py, or any request to add, debug, fix, or extend prediction market data pipelines. Also activates for: probability-weighted price calculations, sparkline data, market bracket mapping, OpenRouter/OpenAI prediction terminal, or BTC market synthesis from multiple events.
---

# Polymarket BTC Synthesis — Working Knowledge

## Active Codebase
Two interchangeable entry points — `poly_ui.py` (OpenAI Reasoning API) and `poly_or.py` (OpenRouter). Both use the same core synthesis logic but initialize different clients for market analysis.

## Event Registry (Memorize)
| Event ID | Type | Description |
|----------|------|-------------|
| **37049** | Broad Ranges | BTC price buckets: <120k, 120–121k, 121–122k, 122–123k, >123k |
| **36060** | Fine Ranges | $2k brackets: <110k, 110–112k, 112–114k, 116–118k, >118k |
| **37057** | Reach/Dip | Volatility markets: reach $123k/$125k/$127k, dip $116k/$118k |

**SKIP**: `"dip to $120k"` in Event 37057 — resolved (BTC already hit $120k). Filter is: `if "dip to $120k" in bracket.lower(): continue`.

---

## Core Functions (Quick Reference)

### `calculate_implied_bitcoin_price(brackets, additional_event_id=36060)`
- The synthesis core. Combines Broad, Fine, and Reach/Dip events.
- Maps brackets to midpoints:
  - Main (37049): `<120k` (115000), `120-121k` (120500), `121-122k` (121500), `122-123k` (122500), `>123k` (125000).
  - Fine (36060): `<110k` (105000), `110-112k` (111000), ..., `>118k` (120000).
  - Reach/Dip (37057): `reach_127k` (127000), `dip_116k` (116000), etc.
- **Data Quality**: If probabilities for a single event sum to >1.05 or <0.95, a quality warning is triggered.

### `format_market_data_for_ai(brackets, event_id)`
- Prepares a JSON snapshot for the AI including the `bitcoin_prediction`.
- **Self-Refining Logic**: Includes instructions for the AI to reflect on its previous prediction accuracy.

---

## Non-Negotiable Guardrails (GEMINI.md)

1. **Dependency Discipline**: `openai` is the sole external dependency. Verify against stdlib before adding packages.
2. **Threading Model**: 
   - Use `threading.Thread(..., daemon=True)`.
   - Polling state dict: `{'data': None, 'last_update': 0, 'updating': False}`.
   - **CRITICAL**: Set `state['updating'] = False` as the FINAL statement inside the async function (never in the main loop).
   - **MANDATORY**: Wrap all state dict writes in `threading.Lock()` (Priority Production Improvement).
3. **Render Discipline**: All `curses` draw calls belong exclusively in the main thread render loop. NEVER call curses from background threads.
4. **History Discipline**:
   - Slice `conversation_history` to `[-16:]` on every append cycle.
   - Cap `ai_price_history` and `btc_price_history` at 100 points.
   - Apply dedup filter: `abs(new - last) > 0.01`.
5. **Output Contract**:
   - Format: `Implied price: $XXX,XXX - [ONE insight ≤100 chars]`.
   - Extraction Regex: `r'\$([0-9,]+)'`.

---

## AI Model Specifics

- **`poly_ui.py`**: Uses `gpt-5-mini` with `reasoning={"effort": "high"}` + `.output_text`.
- **`poly_or.py`**: Uses `moonshotai/kimi-k2` via `client.chat.completions.create()`.
- **Price Smoothing**: Prompt enforces `0.70 * fresh + 0.30 * previous` weighting.

---

## Debugging & Validation

### Arbitrage Detection
Large gaps between `max_prob_range` and the weighted average often indicate a bimodal distribution or stale data. Check if fine (36060) and broad (37049) disagree by >$2k.

### Validation Script Template
If `scripts/validate_event.py` is missing, use the standard `http_get_json` pattern to verify Gamma API response structure for any new Event ID.

→ For full math details → `references/synthesis-math.md`
→ For API pattern contracts → `references/api-patterns.md`

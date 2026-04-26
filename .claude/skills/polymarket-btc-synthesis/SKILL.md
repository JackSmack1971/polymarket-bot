---
name: polymarket-btc-synthesis
description: Polymarket Gamma/CLOB API expert for multi-event Bitcoin prediction synthesis. Use when the user mentions Polymarket, Gamma API, CLOB, event IDs (37049, 36060, 37057), implied Bitcoin price, fetch_event_markets, calculate_implied_bitcoin_price, fine ranges, broad ranges, reach/dip markets, poly_ui.py, poly_or.py, or any request to add, debug, fix, or extend prediction market data pipelines. Also activates for: probability-weighted price calculations, sparkline data, market bracket mapping, OpenRouter/OpenAI prediction terminal, or BTC market synthesis from multiple events.
---

# Polymarket BTC Synthesis — Working Knowledge

## Active Codebase
Two interchangeable entry points — `poly_ui.py` (OpenAI Reasoning API) and `poly_or.py` (OpenRouter).  
Same logic, different `client` initialization. All domain rules below apply to both.

## Event Registry (Memorize)
| Event ID | Type | Description |
|----------|------|-------------|
| **37049** | Broad Ranges | BTC price buckets: <120k, 120–121k, 121–122k, 122–123k, >123k |
| **36060** | Fine Ranges | $2k brackets: <110k, 110–112k, 112–114k, 114–116k, 116–118k, >118k |
| **37057** | Reach/Dip | Volatility markets: reach $123k/$125k/$127k, dip $116k/$118k |

**SKIP**: `"dip to $120k"` in Event 37057 — resolved (BTC already hit $120k). This filter is already in the code; never remove it.

For full bracket-to-midpoint mappings → see `references/event-registry.md`

---

## Core Functions (Quick Reference)

### `fetch_event_markets(event_id)`
- Calls `GAMMA_BASE/events/{event_id}`
- Parses `clobTokenIds`, `outcomePrices`, `outcomes` from each market
- Keeps only `Yes/No` pairs (len==2, outcomes==["Yes","No"])
- Sort order: `<` markets first (0), `between` middle (1), `>` last (2), unknown (9)
- Returns: `[{bracket, yes_token, no_token}]`

### `fetch_price(token_id, side="buy")`
- Calls `CLOB_BASE/price?token_id=...&side=buy`
- Response can be raw float OR `{"price": x}` — both handled
- Returns `float | None`

### `calculate_implied_bitcoin_price(brackets, additional_event_id=36060)`
- The synthesis core. **Never refactor without reading `references/synthesis-math.md` first.**
- Combines all three events, maps brackets to midpoints, computes probability-weighted mean
- Returns: `{implied_price, most_likely_range, max_probability, ranges, data_sources}`
- Weighting: Fine (40%) > Broad (35%) > Reach/Dip (25%)

### `format_market_data_for_ai(brackets, event_id)`
- Builds JSON snapshot for AI system prompt
- Calls `calculate_implied_bitcoin_price()` and attaches result as `bitcoin_prediction`
- Called every 25s by `collect_market_data_async()`

---

## Non-Negotiable Rules

1. **Always synthesize all three events.** Never analyze a single event in isolation.
2. **Never change 40/35/25 weighting** unless user explicitly requests a new model.
3. **Skip resolved dip $120k market** — filter is `if "dip to $120k" in bracket.lower(): continue`
4. **Price consistency rule**: new_prediction = 0.70 × fresh_calc + 0.30 × prev_prediction  
   Exception: only use 100% fresh_calc if probability distribution shifted >2%.  
   **Do not weaken this rule.** It is enforced in the AI system prompt, not in Python.
5. **Fine ranges override broad ranges** when they disagree by >$2k (trust Event 36060 more).
6. **References are one level deep** — `references/*.md` only. No nested paths.

---

## Adding a New Event (Checklist)

When user asks to add event `XXXXX`:
- [ ] Call `fetch_event_markets(XXXXX)` and inspect bracket question text
- [ ] Add bracket-to-midpoint mappings in `calculate_implied_bitcoin_price()` with `source: "new_event_name"`
- [ ] Update weighting comment block (redistribute %, keep total reasoning consistent)
- [ ] Add `fetch_event_markets(XXXXX)` call in `main()` with state initialization loop
- [ ] Pass new brackets into `all_brackets` before `collect_market_data_async()`
- [ ] Run `python scripts/validate_event.py XXXXX` to confirm structure

→ For full implementation blueprint → `references/synthesis-math.md#adding-new-event`

---

## Debugging Price Volatility

If implied price jumps >$2k between cycles:
1. Check `max_prob_range` vs weighted average — large gap = bimodal distribution
2. Inspect whether fine ranges (36060) and broad ranges (37049) disagree by >$2k
3. If yes: trust fine ranges, adjust comment in `calculate_implied_bitcoin_price()`
4. **Do NOT edit the synthesis function** — tighten the AI system prompt's price consistency rules instead
5. Confirm reach/dip (37057) aren't pulling mean via high-midpoint outliers

→ For arbitrage detection math → `references/synthesis-math.md#arbitrage-detection`

---

## Threading Model (Read Before Touching)

| Thread | Interval | Target Function | State Dict |
|--------|----------|-----------------|------------|
| Market data | 25s | `collect_market_data_async()` | `market_state` |
| AI analysis | 30s | `update_ai_analysis_async()` | `ai_state` |
| BTC price | 60s | `update_btc_price_async()` | `btc_state` |

AI thread uses `market_state['current_data']` — never raw brackets directly.  
Conversation history capped at last 16 messages (8 pairs) in `ai_state['conversation_history']`.

---

## API Endpoints (Canonical)

```
GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE  = "https://clob.polymarket.com"
```

Full schema, error handling contracts → `references/api-patterns.md`

---

## Response Format Constraint (AI System Prompt)

Output must be: `"Implied price: $XXX,XXX - [ONE insight, max 100 chars]"`  
- No multi-sentence analysis in terminal output  
- Full reasoning lives in conversation history, not display string

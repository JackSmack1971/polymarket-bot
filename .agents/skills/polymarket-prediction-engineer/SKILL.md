---
name: polymarket-prediction-engineer
description: >
  Specialist for developing, debugging, and tuning the Polymarket Bitcoin AI
  prediction terminal (poly_ui.py / poly_or.py). Activates when the user
  mentions: AI prediction accuracy, implied price, jumps too much, system
  prompt, conversation history, prediction consistency, gpt-5-mini, kimi-k2,
  reasoning API, OpenRouter model swap, output format, sparkline, market
  synthesis, event ID, CLOB, Gamma API, probability-weighted price, reach/dip,
  fine ranges, bracket weights, or extract_ai_price. Also triggers on requests
  to add features, change models, fix terminal display, or improve stability
  of the prediction loop. Do NOT activate for general Python questions unrelated
  to this project.
---

# Polymarket Prediction Engineer

You are the domain expert for this Bitcoin prediction terminal. The codebase
has two near-identical entry points:

| File | AI Provider | Key difference |
|------|-------------|----------------|
| `poly_ui.py` | OpenAI (`gpt-5-mini`) | Uses Responses API + `reasoning={"effort":"high"}` |
| `poly_or.py` | OpenRouter (`moonshotai/kimi-k2`) | Standard chat completions, no reasoning param |

The function `update_ai_analysis_async()` (~lines 300–420 in each file) is
the **most critical function**. It owns the system prompt, conversation memory,
and AI call. Treat it as the intellectual core of the project.

---

## Core Invariants — Never Violate

1. **Output format is sacred**: model MUST return exactly:
   `Implied price: $XXX,XXX - [ONE insight ≤100 chars]`
   — `extract_ai_price()` uses regex `r'\$([0-9,]+)'`; format drift breaks
   the entire display pipeline.

2. **Conversation memory is load-bearing**: 16-message window (8 user + 8
   assistant) gives the AI "prediction tracking" behavior. Never make it
   stateless.

3. **30% previous-prediction anchor**: stabilizes the loop.
   Formula: `new = 0.70 × fresh_calc + 0.30 × prev` when probability
   change < 2%. This is the primary anti-jitter mechanism.

4. **One insight only**: terminal column width is constrained. Multi-insight
   output breaks layout. Do not soften this rule.

---

## Diagnosis Decision Tree

**Symptom → Root Cause → Fix**

```
Predictions jumping >$2k between cycles with no market move?
  └─ Anchor weight too low
     Fix: raise prev-prediction weight 30% → 40% in system prompt
          add: "if Σ|Δp_i| < 3%, move ≤$800"

AI output not matching regex / price not parsing?
  └─ Format drift in model response
     Fix: add few-shot examples to system prompt
          tighten: "return ONLY the line below, no preamble"

AI ignores previous predictions in follow-up turns?
  └─ Conversation history not threading correctly
     Fix: verify messages list is passed correctly in API call
          check first-message guard (no prev to reference on turn 1)

Terminal layout broken / text overflow?
  └─ Insight string >100 chars or multi-line response
     Fix: add hard truncation in wrap_ai_text() as safety net
          tighten 100-char rule in system prompt

Model swap needed (e.g. gpt-5-mini → Claude via OpenRouter)?
  └─ See references/model-swap-guide.md
```

---

## System Prompt Architecture

The system prompt defines the AI as a **quantitative Bitcoin price prediction
specialist** using 6 frameworks. See
`references/ai-system-architecture.md` for the full framework spec and
tuning guidance.

The **PRICE CONSISTENCY RULES** section is the most frequently tuned part.
Template structure:

```
PRICE CONSISTENCY RULES:
- Large price jumps (>$2000) require explicit justification
- If Σ|Δprobability_i| < 2% → move ≤$1000
- Weight previous prediction at [30–50]% unless regime change detected
- Formula: new_price = α × fresh_calc + (1-α) × prev_price
- Regime change = single bracket probability shift >15% in one cycle
```

---

## Probability Synthesis Logic

Three event types feed the implied-price calculation:

| Event type | Role | Weight guidance |
|------------|------|-----------------|
| Broad ranges (e.g. 37049) | Wide anchor | baseline |
| Fine ranges (e.g. 36060) | Precision pull | higher weight when available |
| Reach/dip (e.g. 37057) | Tail signal | asymmetric — use for confidence interval only |

When fine and broad ranges disagree by >$1,500 → trust fine ranges.

---

## Common Modification Patterns

**Add confidence score to output:**
```python
# Change required format to:
# Implied price: $XXX,XXX - [insight] (conf: XX%)
# Update char limit: 100 → 115
# Add instruction: "Append confidence 0-100% in parentheses at end"
```

**Increase stability (more conservative):**
```python
# Raise anchor weight: 30% → 45%
# Add bracket: "if Σ|Δp_i| < 3%, max move = $500"
```

**Change model (OpenRouter):**
```python
# In poly_or.py, find: model = "moonshotai/kimi-k2"
# Replace with target model string
# Remove reasoning param if not supported
# Update wrap_ai_text() prefix string
# See references/model-swap-guide.md for full steps
```

---

## Files Reference Map

```
poly_ui.py
  fetch_event_markets()     ~line  35   Gamma API call, bracket parsing
  fetch_price()             ~line  70   CLOB price fetch
  spark_segments()          ~line  80   Sparkline generation
  update_ai_analysis_async()~line 300   ★ SYSTEM PROMPT + AI CALL + MEMORY
  extract_ai_price()        ~line 420   Regex price parser
  wrap_ai_text()            ~line 435   Terminal text wrapper
  draw_screen()             ~line 450   Curses layout engine

poly_or.py — identical structure, different AI call signature
  update_ai_analysis_async() uses openai.OpenAI(base_url=OPENROUTER_BASE)
  No reasoning parameter
```

For deep function-level detail see `references/function-reference.md`.

---

## Validation

Before shipping any system prompt change, run:

```bash
python scripts/validate_output_format.py "Implied price: $119,250 - 68% mass in 118-120k, mild upward momentum"
# Expected: PASS
python scripts/validate_output_format.py "The implied price is $119,250. Based on my analysis..."
# Expected: FAIL — multi-sentence
```

# AI System Architecture Reference

## System Prompt Role

The system prompt in `update_ai_analysis_async()` defines the model as a
**quantitative Bitcoin price prediction specialist**. It must be treated as
the primary intellectual property of the project. Any change to it directly
affects prediction quality, stability, and output parsability.

---

## The Six Analytical Frameworks

These are declared explicitly in the system prompt and must all remain present
even when making targeted edits. Removing any one degrades coherence.

### 1. Probability Density Function
Model interprets the full bracket distribution as a continuous PDF, not just
the highest-probability bracket. Forces multi-bracket synthesis.

### 2. Expected Value (Probability-Weighted Mean)
`EV = Σ(midpoint_i × p_yes_i)` across all active brackets.
This is the mathematical anchor for the implied price.

### 3. Confidence Intervals
Model must maintain 68% and 95% CI bounds from the bracket distribution.
Used in the confidence score extension (if added).

### 4. Market Efficiency / Arbitrage Detection
System prompt instructs the model to flag if bracket prices sum to >1.05
(over-round) or show clear mispricings. Output is informational only —
never changes the implied price formula.

### 5. Momentum Indicators (Probability Flow)
Δp per bracket between this cycle and last. Used to justify directional
language in the insight string ("upward momentum", "bearish drift").

### 6. Volatility Metrics (Reach/Dip Markets)
Reach events (e.g. "Will BTC reach $125k?") and dip events feed the tail
of the distribution. Their probability informs CI width, not the EV directly.

---

## PRICE CONSISTENCY RULES — Full Tuning Reference

This is the most frequently modified section. The canonical template:

```
PRICE CONSISTENCY RULES:
You have a previous prediction. Apply these rules strictly:

1. Calculate your fresh expected value first (pure math, ignore history).
2. Compute Σ|Δp_i| = sum of absolute probability changes across all brackets.
3. Apply anchoring formula:
   - If Σ|Δp_i| < 2%:  new_price = 0.70 × fresh + 0.30 × previous
   - If Σ|Δp_i| 2–10%: new_price = 0.85 × fresh + 0.15 × previous
   - If Σ|Δp_i| > 10%: use fresh (regime change — full update)
4. Maximum move caps:
   - Σ|Δp_i| < 2%  → max $800 from previous
   - Σ|Δp_i| < 5%  → max $1,500 from previous
   - No cap when regime change detected
5. Fine ranges override broad ranges when they disagree by >$1,500.
```

**Tuning knobs:**
| Stability need | Parameter to change |
|----------------|---------------------|
| More stable | Raise α (anchor weight) from 0.30 → 0.40–0.50 |
| More reactive | Lower α to 0.15–0.20 |
| Tighter jitter cap | Lower move caps ($800 → $400) |
| Regime sensitivity | Lower Σ|Δp_i| threshold from 10% → 7% |

---

## Output Format Spec

The model **must** return one line only:

```
Implied price: $XXX,XXX - [insight string]
```

### Rules enforced by system prompt:
- Price: US dollar format with comma separator, no decimal
- Insight: maximum 100 characters (hard limit)
- Single insight only — no conjunctions ("and also", "but also")
- No preamble, no explanation, no reasoning narration
- No markdown, no line breaks

### Enforced by code:
- `extract_ai_price()` regex: `r'\$([0-9,]+)'` — first match wins
- `wrap_ai_text()` — wraps insight text for terminal column width

### Good examples:
```
Implied price: $119,250 - 68% mass in 118-120k, mild upward momentum
Implied price: $118,900 - Fine ranges pulling down, reach_125k at 0.31
Implied price: $121,400 - Regime shift: <120k bracket dropped 18% this cycle
```

### Bad examples (system prompt must prevent these):
```
The implied price is approximately $119,250 based on my analysis...  ← preamble
Implied price: $119,250 - Strong cluster at 118-120k and bearish signals from reach market  ← two insights
Implied price: $119,250.50 - ...  ← decimal in price
```

---

## Conversation Memory Mechanics

```python
# Canonical structure in update_ai_analysis_async():

# First call (no history):
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": f"Market data:\n{market_summary}"}
]

# Subsequent calls (history exists):
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    *conversation_history[-16:],           # last 8 user + 8 assistant
    {"role": "user", "content":
        f"Here's updated market data. Consider your previous analyses:\n{market_summary}"}
]
```

**Critical invariants:**
- System prompt is always injected fresh (not inside history)
- History window = 16 messages max (prevents context overflow)
- First-message guard prevents "consider your previous" on turn 1
- Never summarize or truncate history — keep raw message objects

---

## API Call Signatures

### poly_ui.py (OpenAI Responses API)
```python
response = client.responses.create(
    model="gpt-5-mini",
    reasoning={"effort": "high"},
    input=messages
)
result = response.output_text
```

### poly_or.py (OpenRouter via OpenAI client)
```python
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"]
)
response = client.chat.completions.create(
    model="moonshotai/kimi-k2",
    messages=messages
)
result = response.choices[0].message.content
```

### Key difference: `reasoning` param only for OpenAI version.
Passing it to OpenRouter will cause an API error on most models.

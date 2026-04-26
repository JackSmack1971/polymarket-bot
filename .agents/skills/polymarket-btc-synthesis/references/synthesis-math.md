# Synthesis Math: Weighting Model & Price Consistency

## Table of Contents
1. [Probability-Weighted Mean Formula](#formula)
2. [Source Weighting Philosophy](#weighting)
3. [Price Consistency Rule](#price-consistency)
4. [Arbitrage Detection](#arbitrage-detection)
5. [Adding a New Event](#adding-new-event)

---

## Formula

`calculate_implied_bitcoin_price()` computes a **probability-weighted mean** across all bracket sources:

```
implied_price = Σ(prob_i × midpoint_i) / Σ(prob_i)
```

Where:
- `prob_i` = `yes_price` (from CLOB buy side) for each bracket
- `midpoint_i` = dollar midpoint of the bracket (see `event-registry.md`)
- Sum spans all three event sources combined

**Return schema:**
```python
{
    "implied_price": int,           # rounded dollar value
    "most_likely_range": str,       # label of bracket with max prob
    "max_probability": float,       # rounded to 3 decimals
    "ranges": list[dict],           # all bracket dicts used
    "data_sources": int             # count of "fine_ranges" entries
}
```

---

## Weighting Philosophy

The **40/35/25** split is philosophical, not mathematical — it represents analytical trust:

| Source | Weight | Rationale |
|--------|--------|-----------|
| Fine Ranges (36060) | **40%** | $2k granularity = highest resolution signal |
| Broad Ranges (37049) | **35%** | Wider buckets, but direct closing-price markets |
| Reach/Dip (37057) | **25%** | Volatility indicators — path-dependent, not closing price |

**Implementation note**: The weight split is conceptual. In the current code, all sources contribute their `prob × mid` equally to the weighted sum — the "weight" is enforced by:
1. Including more fine-grained brackets (more terms in the sum from 36060)
2. Lower midpoints on reach/dip (they pull less on the mean dollar value)
3. The AI system prompt's data hierarchy instruction

**If rebalancing weights explicitly** (user request only):
- Multiply each source's `prob` by its weight scalar before summing
- Example: `fine_prob × 0.40`, `broad_prob × 0.35`, `reach_dip_prob × 0.25`
- Normalize denominator accordingly

---

## Price Consistency Rule

Enforced in the **AI system prompt** (not Python code). Do not "fix" this in Python.

```
new_prediction = 0.70 × fresh_calculation + 0.30 × previous_prediction
```

**Exception**: use 100% fresh calculation only if:
- Probability distribution shifted >2% in any single bracket
- Major macro event (model detects this from bracket momentum)

**Enforcement location**: In `update_ai_analysis_async()`, the system prompt contains:
> "Weight your previous prediction at 30% unless major market shift occurred"
> "New prediction = 70% * fresh_calculation + 30% * previous_prediction (if <2% probability change)"

**Debugging price jumps >$2k:**
1. `max_prob_range` vs weighted mean gap → bimodal = normal, >$3k gap = suspicious
2. Check if fine (36060) and broad (37049) disagree by >$2k → trust fine, log discrepancy
3. Reach/dip high-midpoint outliers pulling mean? → check `reach_127k` prob is not inflated
4. Never edit the synthesis function for this — tighten the AI system prompt

---

## Arbitrage Detection

The AI system prompt flags data quality issues when:
```
sum(all bracket probabilities for a single event) > 1.05 OR < 0.95
```

This indicates either:
- Data staleness (CLOB prices lagging)
- A resolved market still in the feed (e.g., a closed bracket with non-zero price)

**Manual check** (add to `format_market_data_for_ai` if needed):
```python
main_sum = sum(b["last_yes"] for b in brackets if b["last_yes"])
if abs(main_sum - 1.0) > 0.05:
    data["data_quality_warning"] = f"Broad bracket probs sum to {main_sum:.3f}"
```

---

## Adding a New Event

Full checklist (also in SKILL.md summary):

### Step 1: Inspect bracket structure
```python
import json
from urllib.request import urlopen, Request
req = Request(f"https://gamma-api.polymarket.com/events/XXXXX", 
              headers={"User-Agent": "poly-ui/1.0"})
with urlopen(req) as r:
    ev = json.loads(r.read())
for m in ev["markets"][:3]:
    print(m.get("question"), json.loads(m.get("outcomePrices","[]")))
```

### Step 2: Map brackets to midpoints
Add an `elif` block in `calculate_implied_bitcoin_price()`:
```python
# New event XXXXX ($1k fine brackets example)
for x in fetch_additional_event_data(XXXXX):
    bracket = x["bracket"].lower()
    yes_prob = x["yes_price"]
    if "between" in bracket and "119" in bracket and "120" in bracket:
        ranges.append({"range": "119-120k", "prob": yes_prob, "mid": 119500, "source": "ultra_fine"})
    # ... etc
```

### Step 3: Update main() initialization
```python
try:
    new_event_brackets = fetch_event_markets(XXXXX)
except Exception:
    new_event_brackets = []

for b in new_event_brackets:
    b["yes_hist"] = []; b["no_hist"] = []
    b["last_yes"] = None; b["last_no"] = None
    b["event_id"] = XXXXX
```

### Step 4: Add to all_brackets aggregation
```python
all_brackets = brackets + additional_brackets + reach_dip_brackets + new_event_brackets
```

### Step 5: Add display section in main UI loop
Follow the pattern of the `additional_brackets` display block. Adjust `lbl_w` and guard with `if row < h-4`.

### Step 6: Validate
```bash
python scripts/validate_event.py XXXXX
```

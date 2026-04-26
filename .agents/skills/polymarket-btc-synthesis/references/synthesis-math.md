# Synthesis Math: Weighting Model & Price Consistency

## Table of Contents
1. [Probability-Weighted Mean Formula](#formula)
2. [Data Quality Monitoring](#data-quality)
3. [Bimodal Distribution Handling](#bimodal-handling)
4. [Source Weighting Philosophy](#weighting)
5. [Validation Script Template](#validation-template)

---

## Formula

`calculate_implied_bitcoin_price()` computes a **probability-weighted mean** across all bracket sources:

```
implied_price = Σ(prob_i × midpoint_i) / Σ(prob_i)
```

Where:
- `prob_i` = `yes_price` for each bracket.
- `midpoint_i` = dollar midpoint of the bracket.

---

## Data Quality Monitoring

The system monitors for "arbitrage" or stale data by summing probabilities for each event.

**Logic (AI-level):**
- If `sum(event_probabilities) > 1.05` or `< 0.95`, the data is considered suspicious.
- This usually indicates a market has resolved but is still reporting a price, or the CLOB feed is lagging.

**Implementation (Python):**
```python
def check_data_quality(brackets):
    sums_by_event = {}
    for b in brackets:
        eid = b.get("event_id")
        sums_by_event[eid] = sums_by_event.get(eid, 0) + (b.get("last_yes") or 0)
    
    warnings = []
    for eid, s in sums_by_event.items():
        if abs(s - 1.0) > 0.05:
            warnings.append(f"Event {eid} sum {s:.3f} outside 0.95-1.05")
    return warnings
```

---

## Bimodal Distribution Handling

When market mass is split between two distinct clusters (e.g., a "binary outcome" feel where BTC either breaks out to $130k or crashes to $110k), the weighted average can be misleading.

**Detection:**
- If `abs(implied_price - midpoint_of_max_prob_bracket) > $3,000`, the distribution is likely bimodal.
- **Action**: AI should report the "Mode" (most likely range) and mention the "Mean" (weighted average) as a secondary figure.

---

## Source Weighting Philosophy

Analytical trust is distributed as:
- **Fine Ranges (36060)**: 40% (Highest resolution).
- **Broad Ranges (37049)**: 35%.
- **Reach/Dip (37057)**: 25% (Volatility marker).

---

## Validation Script Template

If `scripts/validate_event.py` is missing, use this to verify new event IDs:

```python
import json, sys
from urllib.request import urlopen, Request

def validate(event_id):
    url = f"https://gamma-api.polymarket.com/events/{event_id}"
    req = Request(url, headers={"User-Agent": "poly-ui/1.0"})
    with urlopen(req) as r:
        ev = json.loads(r.read())
    
    print(f"Event: {ev.get('title')}")
    for m in ev.get("markets", []):
        q = m.get("question")
        prices = json.loads(m.get("outcomePrices", "[]"))
        print(f" - {q}: {prices}")

if __name__ == "__main__":
    validate(sys.argv[1])
```

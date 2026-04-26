# Event Registry: Bracket-to-Midpoint Maps

## Event 37049 — Broad Ranges

Bracket keyword patterns and their midpoints used in `calculate_implied_bitcoin_price()`:

| Bracket keyword | Range label | Midpoint | Notes |
|----------------|-------------|----------|-------|
| `"less than"` + `"120"` | `< 120k` | 115,000 | Broad lower tail |
| `"between"` + `"120"` + `"121"` | `120-121k` | 120,500 | |
| `"between"` + `"121"` + `"122"` | `121-122k` | 121,500 | |
| `"between"` + `"122"` + `"123"` | `122-123k` | 122,500 | |
| `"greater than"` + `"123"` | `> 123k` | 125,000 | Broad upper tail |

Source tag: `"main"` | Weight in synthesis: **35%**

---

## Event 36060 — Fine Ranges ($2k brackets)

| Bracket keyword | Range label | Midpoint | Notes |
|----------------|-------------|----------|-------|
| `"less than"` + `"110"` | `< 110k` | 105,000 | Lower tail |
| `"between"` + `"110"` + `"112"` | `110-112k` | 111,000 | |
| `"between"` + `"112"` + `"114"` | `112-114k` | 113,000 | |
| `"between"` + `"114"` + `"116"` | `114-116k` | 115,000 | |
| `"between"` + `"116"` + `"118"` | `116-118k` | 117,000 | |
| `"greater than"` + `"118"` | `> 118k` | 120,000 | Upper tail |

Source tag: `"fine_ranges"` | Weight in synthesis: **40%** (highest — most granular)

---

## Event 37057 — Reach/Dip (Volatility Markets)

| Bracket keyword | Range label | Midpoint | Action |
|----------------|-------------|----------|--------|
| `"reach"` + `"$127k"` | `reach_127k` | 127,000 | Include |
| `"reach"` + `"$125k"` | `reach_125k` | 125,000 | Include |
| `"reach"` + `"$123k"` | `reach_123k` | 123,000 | Include |
| `"dip to"` + `"$120k"` | *(resolved)* | — | **SKIP** — BTC already hit $120k |
| `"dip to"` + `"$118k"` | `dip_118k` | 118,000 | Include |
| `"dip to"` + `"$116k"` | `dip_116k` | 116,000 | Include |

Source tag: `"reach_dip"` | Weight in synthesis: **25%** (lowest — volatility perspective, not closing price)

**Resolved market skip code** (already in codebase, never remove):
```python
elif "dip to" in bracket and "$120k" in bracket:
    continue  # Skip - this market resolved when BTC hit $120k
```

---

## Midpoint Philosophy

- Tail brackets use extrapolated midpoints (not symmetric): `< 120k → 115000`, `> 123k → 125000`  
- Narrow brackets use exact arithmetic midpoint: `120–121k → 120500`  
- Reach/dip midpoints equal the threshold itself (directional markers, not ranges)

---

## Adding a New Event: Midpoint Template

When adding event with `$1k` fine brackets (e.g., 38500):

```python
# In calculate_implied_bitcoin_price(), new elif block:
if "between" in bracket and "119" in bracket and "120" in bracket:
    ranges.append({"range": "119-120k", "prob": yes_prob, "mid": 119500, "source": "ultra_fine"})
elif "between" in bracket and "120" in bracket and "121" in bracket:
    ranges.append({"range": "120-121k", "prob": yes_prob, "mid": 120500, "source": "ultra_fine"})
# ... continue for all $1k brackets
```

Recommend weight: 45% for $1k brackets. Reduce fine_ranges (36060) from 40% to 30%.  
Update weighting comment block at top of function.

---

## Known Resolution States

| Market | Status | Action |
|--------|--------|--------|
| Event 37057: dip $120k | **Resolved (BTC hit $120k)** | Skip in all processing |
| All others | Active | Include normally |

Always check `market.get("closed")` or `market.get("resolved")` fields from Gamma API when unsure.

# API Endpoints & Call Patterns

## Table of Contents
1. [Polymarket Gamma API](#1-polymarket-gamma-api)
2. [Polymarket CLOB API](#2-polymarket-clob-api)
3. [CoinGecko BTC Price](#3-coingecko-btc-price)
4. [OpenAI Responses API Pattern](#4-openai-responses-api-pattern)
5. [OpenRouter Fallback Pattern](#5-openrouter-fallback-pattern)

---

---

## 1. Polymarket Gamma API

```
Base: https://gamma-api.polymarket.com

GET /events/{event_id}         → full event with markets array
GET /markets/{market_id}       → single market detail
```

### Event IDs & Sources
| ID | Category | Usage | Role |
|---|---|---|---|
| **User Defined** | Variable | `main -e ID` | Primary prediction target |
| **36060** | Fine Ranges | Hardcoded | Precision calibration ($2k brackets) |
| **37057** | Reach/Dip | Hardcoded | Volatility & tail risk signals |

**Note**: All three events are synthesized in `collect_market_data_async` to form the `current_data` snapshot for the AI.

---

## 2. Polymarket CLOB API

```
Base: https://clob.polymarket.com

GET /price?token_id={id}&side=BUY   → {"price": "0.72"}
GET /price?token_id={id}&side=SELL  → {"price": "0.70"}
```

---

## 3. Implied Price Logic

The function `calculate_implied_bitcoin_price(brackets)` synthesizes data:
1. **Extract Midpoints**: Parse labels (e.g., "$120-121k" → 120500).
2. **Collect Probabilities**: Get `last_yes` price for each bracket.
3. **Weight Ranges**: Combine Broad, Fine, and Reach/Dip ranges.
4. **Calculate Mean**: `Σ(midpoint * prob) / Σ(probs)`.

---

## 4. AI Call Patterns

### OpenAI Reasoning API (poly_ui.py)
Used for deep analysis of probability distributions.

```python
model = "gpt-5-mini"
effort = "high"
response = client.responses.create(
    model=model,
    reasoning={"effort": effort},
    input=messages
)
```

### OpenRouter (poly_or.py)
Used for model flexibility (e.g., Moonshot Kimi).

```python
model = "moonshotai/kimi-k2"
response = client.chat.completions.create(
    model=model,
    messages=messages
)
```

### Conversation History
History is sliced to `[-16:]` (8 pairs) to maintain context without exceeding token limits.
```python
ai_state['conversation_history'] = ai_state['conversation_history'][-16:]
```

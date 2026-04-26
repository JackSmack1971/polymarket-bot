# API Endpoints & Call Patterns

## Table of Contents
1. [Polymarket Gamma API](#1-polymarket-gamma-api)
2. [Polymarket CLOB API](#2-polymarket-clob-api)
3. [CoinGecko BTC Price](#3-coingecko-btc-price)
4. [AI Model Identifiers](#4-ai-model-identifiers)
5. [α-Tuning & Regime Logic](#5-%CE%B1-tuning--regime-logic)

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
| **User Defined** | Variable | `main.py -e ID` | Primary prediction target |
| **36060** | Fine Ranges | Hardcoded | Precision calibration ($2k brackets) |
| **37057** | Reach/Dip | Hardcoded | Volatility & tail risk signals |

**Note**: All three events are synthesized in `PredictionService.calculate_implied_price`.

---

## 2. Polymarket CLOB API

```
Base: https://clob.polymarket.com

GET /price?token_id={id}&side=BUY   → {"price": "0.72"}
GET /price?token_id={id}&side=SELL  → {"price": "0.70"}
```

---

## 3. Implied Price Logic (PredictionService)

The function `calculate_implied_price(main, fine, tail)` in `src/services/prediction_service.py` synthesizes data:
1. **Extract Midpoints**: Parse labels (e.g., "$120-121k" → 120500).
2. **Collect Probabilities**: Get `last_yes` price for each bracket.
3. **Weight Ranges**: Combine Broad, Fine, and Reach/Dip ranges.
4. **Calculate PSI**: Probability Shift Index measures divergence from previous distribution.

---

## 4. AI Model Identifiers

### OpenAI (AIService)
Used for deep reasoning via the Responses API.
- **Model**: `gpt-5-mini`
- **Reasoning**: `{"effort": "high"}`

### OpenRouter (AIService)
Fallback for specific models.
- **Model**: `moonshotai/kimi-k2`

---

## 5. α-Tuning & Regime Logic

AI Analysis follows a deterministic regime based on PSI:
1. **STABLE** (PSI < 0.02): α = 0.70. Anchor to history. Move limit: $800.
2. **MOMENTUM** (PSI 0.02 - 0.10): α = 0.85. Follow fresh data. Move limit: $1,500.
3. **REGIME CHANGE** (PSI > 0.10): α = 1.00. Market reset. No move limit.

---

## 6. Conversation History
History is sliced to `[-16:]` (8 pairs) to maintain context.
```python
# Inside AIService.generate_analysis
messages.extend(history[-16:]) 
```


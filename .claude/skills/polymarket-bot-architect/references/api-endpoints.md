# API Endpoints & Call Patterns

## Table of Contents
1. [Polymarket Gamma API](#1-polymarket-gamma-api)
2. [Polymarket CLOB API](#2-polymarket-clob-api)
3. [CoinGecko BTC Price](#3-coingecko-btc-price)
4. [OpenAI Responses API Pattern](#4-openai-responses-api-pattern)
5. [OpenRouter Fallback Pattern](#5-openrouter-fallback-pattern)

---

## 1. Polymarket Gamma API

```
Base: https://gamma-api.polymarket.com

GET /events/{event_id}         → full event with markets array
GET /markets/{market_id}       → single market detail
```

Key fields from `/events/{event_id}`:
- `markets[].clobTokenIds` — JSON string of [yes_token_id, no_token_id]
- `markets[].outcomePrices` — JSON string of [yes_price, no_price]
- `markets[].outcomes` — JSON string, expected ["Yes", "No"]
- `markets[].question` — bracket label string

---

## 2. Polymarket CLOB API

```
Base: https://clob.polymarket.com

GET /price?token_id={id}&side=BUY   → {"price": "0.72"}
GET /price?token_id={id}&side=SELL  → {"price": "0.70"}
GET /book?token_id={id}             → order book depth
```

Note: `/price` may return a raw float string, not JSON. `http_get_json()` handles this.

---

## 3. CoinGecko BTC Price

```
GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd

Response: {"bitcoin": {"usd": 94500.0}}
```

Extraction:
```python
data = http_get_json(url)
price = data['bitcoin']['usd']
btc_state['price'] = price
```

---

## 4. OpenAI Responses API Pattern

Used in `update_ai_analysis_async()`. Key parameters:

```python
response = client.responses.create(
    model=model,           # e.g. "o4-mini"
    reasoning={"effort": effort},   # "low" | "medium" | "high"
    input=messages,        # list of {role, content} dicts
    max_output_tokens=800
)
result = response.output_text.strip()
```

Message list structure:
```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    *ai_state['conversation_history'][-16:],   # last 16 messages
    {"role": "user", "content": json.dumps(current_data, indent=2)}
]
```

After response, append both turns to history:
```python
ai_state['conversation_history'].append({"role": "user",    "content": user_msg})
ai_state['conversation_history'].append({"role": "assistant","content": result})
ai_state['conversation_history'] = ai_state['conversation_history'][-16:]
```

---

## 5. OpenRouter Fallback Pattern

Used when OpenAI Responses API is not available:

```python
or_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", "")
)
response = or_client.chat.completions.create(
    model=model,
    messages=messages,
    max_tokens=800
)
result = response.choices[0].message.content.strip()
```

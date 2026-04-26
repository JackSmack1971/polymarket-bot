# AI Analysis Reference

## Provider Split

| File | Provider | Client Init | Model | API style |
|---|---|---|---|---|
| `poly_ui.py` | OpenAI | `client = OpenAI()` | `gpt-5-mini` | `client.responses.create(model, reasoning={effort}, input=messages)` |
| `poly_or.py` | OpenRouter | `client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=...)` | `moonshotai/kimi-k2` | `client.chat.completions.create(model, messages)` |

**Important**: `poly_ui.py` uses the **Responses API** (`client.responses.create`), not Chat Completions. Output is in `response.output_text`. OpenRouter uses standard Chat Completions — output in `response.choices[0].message.content`.

## Async Entry Point

```python
def update_ai_analysis_async(current_data, previous_data, ai_state):
    # runs in daemon thread
    # reads ai_state['conversation_history']
    # writes ai_state['analysis'], ['model'], ['effort'], ['last_update']
    # sets ai_state['updating'] = False as final line
```

## Conversation Memory

```python
ai_state['conversation_history']  # list of {role, content} dicts
# Max 16 entries = 8 user/assistant pairs
# Truncated with: ai_state['conversation_history'] = ai_state['conversation_history'][-16:]
```

Messages injected into each call:
1. System prompt (always first)
2. Last 16 history messages (older context)
3. Current prompt (new market data)

## System Prompt (condensed key rules)

**Analytical framework** (weights used for implied price):
- Fine ranges (Event 36060): 40% weight
- Broad ranges (Event 37049): 35% weight  
- Reach/Dip (Event 37057): 25% weight

**Price consistency rules**:
- Jumps >$2000 require justification
- If <2% probability change: `new = 0.7 * fresh + 0.3 * previous`
- When fine/broad disagree >$2k: trust fine ranges

**Data quality flags**:
- If `sum(related probabilities) > 1.05 or < 0.95` → flag quality issue

## Output Format (locked — never change)

```
"Implied price: $XXX,XXX - [ONE key insight, max 100 chars]"
```

Examples:
- ✅ `"Implied price: $119,250 - 68% mass in 118-120k, mild upward momentum"`
- ❌ Long explanations with calculations in the output text

## First vs Subsequent Calls

**First call** (`len(conversation_history) == 0`):
```
Analyze these Bitcoin prediction markets and provide:
1. Your own implied Bitcoin price estimate
2. Brief reasoning based on the probability distributions
Current market data: {json}
Format: "Implied price: $X - [brief analysis]"
```

**Subsequent calls**:
```
Here's updated market data. Consider your previous analyses:
CURRENT MARKET DATA: {json}
1. Your new implied price estimate
2. Brief explanation of changes in market sentiment
3. Reflection on prediction accuracy
Format: "Implied price: $X - [brief analysis of changes and accuracy]"
```

## Modifying the AI Behavior

### Change model (poly_ui.py)
```python
model = "gpt-5-mini"   # change here
effort = "high"         # change here ("low", "medium", "high")
```

### Change model (poly_or.py)
```python
model = "moonshotai/kimi-k2"  # any OpenRouter model slug
```

### Extend conversation memory
```python
# Change the slice limit (currently -16 = 8 pairs)
for hist in ai_state['conversation_history'][-24:]:  # 12 pairs
# AND update the trim line:
ai_state['conversation_history'] = ai_state['conversation_history'][-24:]
```

### Add a new analytical metric to the system prompt
Insert after the existing "Key calculations" section. Keep additions under 5 lines — system prompt token cost is paid every call.

### Change output format
Update the format instruction in BOTH the system prompt and both prompt strings (first-call and subsequent-call). Must be consistent across all three locations.

## AI State in Render Loop

```python
# AI price extracted from analysis string for chart history:
ai_price = None
if ai_state['analysis']:
    # parse "Implied price: $XXX,XXX" from the analysis string
    # extracted via regex or string split on '$'
```

## Background Thread Trigger

```python
# In render loop — triggers new AI call when:
# 1. Not currently updating
# 2. Market data available
# 3. Either: first call, OR enough time has passed since last update
if not ai_state['updating'] and market_state['current_data']:
    ai_state['updating'] = True
    t = threading.Thread(target=update_ai_analysis_async, ...)
    t.daemon = True
    t.start()
```

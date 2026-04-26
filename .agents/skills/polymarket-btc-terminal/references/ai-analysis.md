# AI Analysis Reference

## Provider Split

| File | Provider | Client Init | Model | API style |
|---|---|---|---|---|
| `poly_ui.py` | OpenAI | `client = OpenAI()` | `gpt-5-mini` | `client.responses.create(model, reasoning={effort:"high"}, input=messages)` |
| `poly_or.py` | OpenRouter | `client = OpenAI(base_url="...", api_key=...)` | `moonshotai/kimi-k2` | `client.chat.completions.create(model, messages)` |

## Memory Management

### Conversation History
- **Limit**: Last 16 messages (8 interaction pairs).
- **Trimming**: `ai_state['conversation_history'] = ai_state['conversation_history'][-16:]`.
- **Injection**: History is injected between the System Prompt and the Current Prompt.

## System Prompt Logic

### Analysis Framework
- **Weights**: Fine (40%) > Broad (35%) > Reach/Dip (25%).
- **Arbitrage**: Detect if sum of probabilities is outside 0.95 - 1.05.
- **Consistency**: `New = 0.7 * Fresh + 0.3 * Previous` (unless mass shift > 2%).

### Output Contract
```
"Implied price: $XXX,XXX - [ONE insight, max 100 chars]"
```
The extraction regex in `extract_ai_price()` is `r'\$([0-9,]+)'`.

## Async Workflow

1. Trigger thread if `updating == False` and market data exists.
2. Build `messages` list (System + History + Current Prompt).
3. Call API based on backend (`responses.create` vs `chat.completions.create`).
4. Update `ai_state` with response and metadata (`model`, `effort`).
5. **CRITICAL**: Set `ai_state['updating'] = False` in the `finally` block of the thread.

# Model Swap Guide

## When to Use This Reference
When the user asks to change the AI model (e.g. gpt-5-mini → Claude,
Llama, Gemini, etc.) or switch between OpenAI and OpenRouter providers.

---

## OpenRouter Model Strings (Common)

| Model | String |
|-------|--------|
| Claude Sonnet 4 | `anthropic/claude-sonnet-4-5` |
| Claude Opus 4 | `anthropic/claude-opus-4` |
| Kimi K2 (default) | `moonshotai/kimi-k2` |
| Llama 3.3 70B | `meta-llama/llama-3.3-70b-instruct` |
| Gemini 2.5 Flash | `google/gemini-2.5-flash` |
| DeepSeek R2 | `deepseek/deepseek-r1` |

Check https://openrouter.ai/models for current availability and pricing.

---

## Full Swap Checklist (poly_or.py)

1. **Change model string:**
   ```python
   # Find: model = "moonshotai/kimi-k2"
   # Replace: model = "anthropic/claude-sonnet-4-5"
   ```

2. **Remove reasoning param** (if copying from poly_ui.py):
   ```python
   # OpenRouter doesn't use: reasoning={"effort": "high"}
   # Remove or comment out
   ```

3. **Update display prefix** in `wrap_ai_text()`:
   ```python
   # Find the model name string used in the terminal header
   # Update to reflect new model (e.g. "[claude-sonnet]>")
   ```

4. **Check response extraction:**
   ```python
   # poly_or.py uses:
   result = response.choices[0].message.content
   # This works for all standard OpenRouter models
   ```

5. **Test output format** before deploying:
   ```bash
   python scripts/validate_output_format.py --live
   ```

---

## Switching poly_ui.py to Claude via API (direct Anthropic)

If you want to use the Anthropic API directly instead of OpenRouter:

```python
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

response = client.messages.create(
    model="claude-sonnet-4-5-20251001",
    max_tokens=256,
    system=SYSTEM_PROMPT,            # system goes here, NOT in messages
    messages=conversation_messages   # exclude system message from list
)
result = response.content[0].text
```

**Important:** Anthropic SDK separates `system` from `messages`.
The conversation_history must NOT include the system prompt object.

---

## Model Capability Notes for This Use Case

| Capability | Requirement | Notes |
|------------|-------------|-------|
| Short structured output | Critical | All listed models handle this well |
| Instruction following | Critical | Claude / GPT-5 strongest |
| Numerical reasoning | High | Kimi K2, Claude, GPT-5 all reliable |
| Context retention | High | All models handle 16-msg window fine |
| Speed (<2s response) | Medium | Flash/Haiku fastest; Opus slowest |

For prediction consistency quality: Claude Sonnet ≥ Kimi K2 > Llama 70B.
For speed/cost: Gemini Flash, Haiku fastest.

# Model Swap Guide

## Steps to Swap Models

### 1. Identify Backend
- OpenAI: `poly_ui.py`
- OpenRouter: `poly_or.py`

### 2. Update Model String
Find the `model = "..."` assignment (~line 455 or ~line 461) and replace it with the target model ID (e.g., `gpt-4o`, `anthropic/claude-3-5-sonnet`).

### 3. Handle Reasoning Parameter (OpenAI Only)
If the model supports the OpenAI Responses API reasoning (e.g., `o1`, `gpt-5-mini`), you can set the effort:
```python
reasoning={"effort": "high"} # or "medium", "low"
```
**CAUTION**: Most non-reasoning models will error if this parameter is passed. In `poly_or.py`, the reasoning parameter is explicitly omitted to ensure compatibility with OpenRouter's API surface.

### 4. Adjust History Window
If the new model has a large context window, you can increase `conversation_history[-16:]`. Note that increasing history improves trend analysis but increases token cost per cycle. Maintain the same slice in both the history accumulation and the prompt construction logic.

### 5. Validate Output Format
Run the validation script to ensure the new model follows the rigid output contract:
```bash
python scripts/validate_output_format.py "<model_output>"
```

### 6. Monitor Jitter
Different models have different "stability" levels. You may need to tune the `α` anchor weights in the system prompt specifically for the new model's persona if it tends to overreact to small probability shifts.

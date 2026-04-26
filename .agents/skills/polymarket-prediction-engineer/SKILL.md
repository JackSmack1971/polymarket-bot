---
name: polymarket-prediction-engineer
description: Specialist for developing, debugging, and tuning the Polymarket Bitcoin AI prediction terminal. Focuses on AI prompt engineering, prediction accuracy, and consistency.
---

# Polymarket Prediction Engineer

Expert for the AI prediction logic in `poly_ui.py` and `poly_or.py`.

## Core Invariants

1. **Output Format**: Must be exactly `Implied price: $XXX,XXX - [ONE insight ≤100 chars]`.
2. **Anchor Rule (α-Tuning)**: `new_price = α × fresh + (1-α) × prev_price`.
   - **Stable Market (<2% prob shift)**: α = 0.70 / (1-α) = 0.30
   - **Momentum Shift (2-10% prob shift)**: α = 0.85 / (1-α) = 0.15
   - **Regime Change (>10% prob shift)**: α = 1.00 / (1-α) = 0.00
3. **Concurrency Guard**: All writes to shared state (`ai_state`, `market_state`) MUST be wrapped in `threading.Lock()`.
4. **Memory**: Rigid 16-message history window (8 user/assistant pairs) is required for trend tracking.

---

## Prediction Frameworks

The AI analyzes data using six primary frameworks:
- **PDF Analysis**: Interprets market brackets as a probability density function.
- **Expected Value (EV)**: The probability-weighted mean is the core price anchor.
- **Confidence Intervals**: 68% and 95% CI bounds derived from the distribution.
- **Data Quality Gate**: AI flags if probabilities sum to >1.05 or <0.95 (arbitrage/stale data).
- **Momentum**: Tracks probability flow between adjacent brackets.
- **Volatility**: Uses reach/dip markets (e.g., Event 37057) as asymmetric tail signals.

---

## Self-Reflection & Accuracy

The AI is instructed to reflect on its own performance. In subsequent turns, the prompt explicitly asks for:
- "Reflection on how your previous predictions are performing."
- This is achieved by passing the full conversation history where the AI can see its previous estimate and compare it to the "Current" market state.

---

## Few-Shot Examples (System Prompt Tuning)

To ensure the rigid output format, use these examples in the prompt:

- **First Turn**: "Analyze these markets... Provide implied price and brief reasoning."
- **Subsequent Turns**: "Consider your previous analyses... Provide new price and reflection on accuracy."

**Output Requirement**:
- ✅ `Implied price: $119,250 - 68% mass in 118-120k, mild upward momentum`
- ❌ `The implied price is approximately $119,250. My analysis shows...`

---

## Model Specific Tuning

### OpenAI (gpt-5-mini)
- Uses `client.responses.create` with `reasoning={"effort": "high"}`.
- High effort is required for stable mathematical synthesis.

### OpenRouter (moonshotai/kimi-k2)
- Standard chat completions. Ensure no `reasoning=` parameter is passed to avoid API errors.

→ For full system prompt specification → `references/ai-system-architecture.md`

# AI System Architecture Reference

## Price Consistency Rules (α Tuning)

This is the primary stability mechanism. Formula: `new_price = α × fresh + (1-α) × prev_price`.

| Scenario | Threshold (Σ|Δp_i|) | fresh (α) | prev (1-α) |
|---|---|---|---|
| Stable Market | < 2% | 0.70 | 0.30 |
| Momentum Shift | 2–10% | 0.85 | 0.15 |
| Regime Change | > 10% | 1.00 | 0.00 |

### Move Caps
- **Stable**: Max $800 move per cycle.
- **Moderate**: Max $1,500 move per cycle.
- **Regime Change**: No cap.

---

## Data Quality Analysis (Over-round Gate)

The model is explicitly tasked with identifying market inefficiencies:
- **Sum-of-probs > 1.05**: Indicates an "over-round" (too much probability mass). Usually means stale prices on resolved brackets.
- **Sum-of-probs < 0.95**: Indicates a gap in market coverage or liquidity.

AI Output Action: Mention data quality issues in the insight string if severe.

---

## Accuracy Reflection Pattern

In `update_ai_analysis_async()`, the AI sees its own history. The prompt directs the model to:
1. "Look at your previous Implied Price estimate."
2. "Compare it to the current market consensus."
3. "Briefly explain if you were too high/low and adjust the new prediction based on this historical accuracy trend."

This "closed-loop" feedback is what differentiates the prediction engine from a simple weighted mean.

---

## Extraction Specification

The code uses regex `r'\$([0-9,]+)'` to find the price.
- **Constraint**: The AI must return exactly: `Implied price: $XXX,XXX - [ONE insight ≤100 chars]`.
- **Constraint**: The history is sliced to `[-16:]` (8 turns) on every append cycle.
- **Constraint**: No decimals. Comma separator only in the price string.

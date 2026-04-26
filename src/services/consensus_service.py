"""
Consensus Service — Multi-Model Ensemble Intelligence
Queries two independent AI providers (OpenAI + OpenRouter) and uses a
lightweight "Judge Model" to resolve divergence above CONSENSUS_DIVERGENCE_THRESHOLD.
"""
import logging
import json
from typing import Dict, Any, List, Optional
from openai import OpenAI
from src.core.config import (
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OPENROUTER_MODEL,
    CONSENSUS_DIVERGENCE_THRESHOLD,
    CONSENSUS_JUDGE_MODEL,
)


class ConsensusService:
    """
    Ensemble agent that:
    1. Queries OpenAI primary model.
    2. Queries OpenRouter secondary model.
    3. Averages when within threshold; calls a Judge when divergent.
    """

    def __init__(self):
        self._openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self._openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )

    def resolve(
        self,
        messages: List[Dict[str, str]],
        openai_result: Dict[str, Any],
        openrouter_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Given two independently generated analysis dicts, resolve into a consensus.
        Returns a result dict that matches the AIService output contract.
        """
        p1 = openai_result.get("implied_price", 0)
        p2 = openrouter_result.get("implied_price", 0)

        if p1 == 0 or p2 == 0:
            # One model failed — return the surviving result
            winner = openai_result if p1 else openrouter_result
            winner["consensus_note"] = "One model failed; single-model result used."
            return winner

        divergence = abs(p1 - p2)
        logging.info(f"ConsensusService: OpenAI=${p1:,} | OpenRouter=${p2:,} | Divergence=${divergence:,}")

        if divergence <= CONSENSUS_DIVERGENCE_THRESHOLD:
            # Models agree — simple average
            consensus_price = int((p1 + p2) / 2)
            insight = openai_result.get("insight", "")
            return {
                "content": f"Implied price: ${consensus_price:,} - {insight}",
                "implied_price": consensus_price,
                "insight": insight,
                "internal_audit": (
                    f"[CONSENSUS] OpenAI=${p1:,} | OpenRouter=${p2:,} | Averaged.\n"
                    + openai_result.get("internal_audit", "")
                ),
                "model": f"{DEFAULT_OPENAI_MODEL}+{DEFAULT_OPENROUTER_MODEL}",
                "consensus_note": f"Averaged (divergence=${divergence:,})",
            }
        else:
            # Models diverge — call the Judge
            return self._arbitrate(messages, openai_result, openrouter_result, p1, p2)

    def _arbitrate(
        self,
        messages: List[Dict[str, str]],
        r1: Dict[str, Any],
        r2: Dict[str, Any],
        p1: int,
        p2: int,
    ) -> Dict[str, Any]:
        """Call a fast, cheap Judge Model to resolve divergence."""
        judge_messages = [
            {
                "role": "system",
                "content": (
                    "You are a financial arbitration model. Two specialist models have disagreed on "
                    "an implied Bitcoin price from Polymarket data. Evaluate both reasonings and "
                    "output only the integer price you believe is correct. No explanation."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Model A (OpenAI) implied: ${p1:,}\nReasoning: {r1.get('internal_audit', 'N/A')[:500]}\n\n"
                    f"Model B (OpenRouter) implied: ${p2:,}\nReasoning: {r2.get('internal_audit', 'N/A')[:500]}\n\n"
                    f"Which price is correct? Reply with only the integer, e.g. 105000"
                ),
            },
        ]

        try:
            response = self._openai_client.chat.completions.create(
                model=CONSENSUS_JUDGE_MODEL,
                messages=judge_messages,
                max_tokens=20,
            )
            judge_raw = response.choices[0].message.content.strip().replace(",", "").replace("$", "")
            judged_price = int(judge_raw)
            insight = r1.get("insight", "") if abs(judged_price - p1) < abs(judged_price - p2) else r2.get("insight", "")
            logging.info(f"ConsensusService: Judge ruled ${judged_price:,} (divergence was ${abs(p1-p2):,})")
            return {
                "content": f"Implied price: ${judged_price:,} - {insight}",
                "implied_price": judged_price,
                "insight": insight,
                "internal_audit": (
                    f"[JUDGE] OpenAI=${p1:,} | OpenRouter=${p2:,} | Judge={judged_price:,}\n"
                    + r1.get("internal_audit", "")
                ),
                "model": f"Judge({CONSENSUS_JUDGE_MODEL})",
                "consensus_note": f"Judge arbitrated (divergence=${abs(p1-p2):,})",
            }
        except Exception as e:
            logging.error(f"ConsensusService: Judge model failed: {e}. Falling back to OpenAI result.")
            r1["consensus_note"] = f"Judge failed ({e}); OpenAI result used."
            return r1

import json
import time
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
from src.core.config import (
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OPENROUTER_MODEL,
    CONSENSUS_MODE,
)

class AIAnalysisResponse(BaseModel):
    internal_audit: str = Field(description="Step-by-step reasoning, arbitrage check, and skew analysis.")
    implied_price: int = Field(description="The final synthesized Bitcoin price estimate.")
    insight: str = Field(description="A concise market insight (max 100 chars).")

class AIService:
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        if provider == "openai":
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            self.model = DEFAULT_OPENAI_MODEL
        else:
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_API_KEY
            )
            self.model = DEFAULT_OPENROUTER_MODEL

        # Lazy-import to avoid circular imports at module load
        self._consensus: Any = None
        if CONSENSUS_MODE:
            from src.services.consensus_service import ConsensusService
            self._consensus = ConsensusService()
            # Secondary client for consensus (always the opposite provider)
            if provider == "openai":
                self._secondary_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=OPENROUTER_API_KEY,
                )
                self._secondary_model = DEFAULT_OPENROUTER_MODEL
            else:
                self._secondary_client = OpenAI(api_key=OPENAI_API_KEY)
                self._secondary_model = DEFAULT_OPENAI_MODEL

    def generate_analysis(self, current_data: Dict[str, Any], history: List[Dict[str, str]], last_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI market analysis with deterministic α-Tuning and Structured Outputs."""
        system_prompt = self._get_system_prompt()
        user_prompt = self._get_user_prompt(current_data, last_metadata)

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history[-16:])
        messages.append({"role": "user", "content": user_prompt})

        primary_result = self._call_model(self.client, self.model, messages, self.provider)

        if CONSENSUS_MODE and self._consensus is not None:
            secondary_provider = "openrouter" if self.provider == "openai" else "openai"
            secondary_result = self._call_model(
                self._secondary_client, self._secondary_model, messages, secondary_provider
            )
            return self._consensus.resolve(messages, primary_result, secondary_result)

        return primary_result

    def _call_model(
        self,
        client: OpenAI,
        model: str,
        messages: list,
        provider: str,
        last_metadata: Optional[Dict[str, Any]] = None,
        current_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Delegate to _raw_call — public-facing wrapper for consensus use."""
        return self._raw_call(client, model, messages, provider, last_metadata, current_data)

    def _raw_call(
        self,
        client: OpenAI,
        model: str,
        messages: list,
        provider: str,
        last_metadata: Optional[Dict[str, Any]] = None,
        current_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a single LLM call and parse the structured response."""
        if last_metadata is None:
            last_metadata = {}
        if current_data is None:
            current_data = {}

        try:
            # Determine if we can use structured outputs
            use_structured = provider == "openai" or "gpt-4o" in model or "claude-3-5" in model

            kwargs: Dict[str, Any] = {
                "model": model,
                "messages": messages,
            }

            if use_structured:
                kwargs["response_format"] = AIAnalysisResponse
            elif provider == "openrouter":
                kwargs["response_format"] = {"type": "json_object"}
                messages[0]["content"] += (
                    '\n\nReturn your response as a JSON object matching this schema: '
                    '{"internal_audit": "...", "implied_price": 123456, "insight": "..."}'
                )

            if provider == "openai" and "o3" in model:
                kwargs["reasoning_effort"] = "high"

            response = (
                client.beta.chat.completions.parse(**kwargs)
                if use_structured
                else client.chat.completions.create(**kwargs)
            )

            if use_structured:
                analysis = response.choices[0].message.parsed
                internal_audit = analysis.internal_audit
                implied_price = analysis.implied_price
                insight = analysis.insight
            else:
                raw_content = response.choices[0].message.content.strip()
                try:
                    parsed = json.loads(raw_content)
                    internal_audit = parsed.get("internal_audit", "N/A")
                    implied_price = parsed.get("implied_price", 0)
                    insight = parsed.get("insight", raw_content[:100])
                except json.JSONDecodeError:
                    price_match = re.search(r'\$([0-9,]+)', raw_content)
                    implied_price = int(price_match.group(1).replace(',', '')) if price_match else 0
                    internal_audit = "Parsing failed. Raw output used."
                    insight = raw_content[:100]

            # Move Cap Enforcement
            if implied_price > 0 and last_metadata.get("prev_price"):
                new_p = float(implied_price)
                prev_p = last_metadata["prev_price"]
                psi = current_data.get("mathematical_synthesis", {}).get("psi", 0.0)
                cap = 800 if psi < 0.02 else 1500 if psi < 0.10 else float('inf')
                if abs(new_p - prev_p) > cap:
                    clamped_p = prev_p + (cap if new_p > prev_p else -cap)
                    implied_price = int(clamped_p)
                    insight += f" [Clamped: PSI={psi:.3f}]"

            content = f"Implied price: ${implied_price:,} - {insight}"

            return {
                "content": content,
                "implied_price": implied_price,
                "insight": insight,
                "internal_audit": internal_audit,
                "model": model,
            }
        except Exception as e:
            import logging
            logging.error(f"AI Service Error ({model}): {e}")
            return {"content": f"AI unavailable: {str(e)[:30]}...", "error": True, "implied_price": 0}

    def _get_system_prompt(self) -> str:
        return """You are a quantitative Bitcoin price prediction specialist analyzing Polymarket prediction markets.
Your primary objective is to synthesize multiple probability sources into a single implied price while maintaining consistency via α-Tuning.

### ALPHA-TUNING REGIMES (DETERMINISTIC)
1. STABLE (PSI < 0.02): α = 0.70. Anchor heavily to history. Move limit: $800.
2. MOMENTUM (PSI 0.02 - 0.10): α = 0.85. Follow fresh data. Move limit: $1,500.
3. REGIME CHANGE (PSI > 0.10): α = 1.00. Market reset. No move limit.

### ANALYTICAL PRIORITIES
1. Trust Hierarchy: Fine Ranges (36060) have 40% weight.
2. Arbitrage: Flag if `arbitrage_detected` is True (e.g., Reach prob > Range prob).
3. Liquidity: Factor in `total_volume`. Low volume (<$10k) reduces signal reliability.
4. Skew: Use Reach/Dip markets (Tail Risk) to adjust the EV. 

### REASONING PROTOCOL (INTERNAL AUDIT)
Before outputting the price, you MUST perform an internal audit:
- Check for probability sum consistency in main markets.
- Compare Fine Ranges EV vs Main Market EV.
- Identify any "tail-risk" skew from Reach/Dip markets.
- Calculate the final EV based on the assigned α-Tuning regime.

### OUTPUT CONTRACT
You must return a structured response with:
- `internal_audit`: Your detailed reasoning process (Hidden from TUI).
- `implied_price`: The final integer Bitcoin price estimate.
- `insight`: A single concise sentence (max 100 chars) explaining the move."""

    def _get_user_prompt(self, data: Dict[str, Any], last_metadata: Dict[str, Any]) -> str:
        synthesis = data.get("mathematical_synthesis", {})
        psi = synthesis.get("psi", 0.0)
        regime = "STABLE" if psi < 0.02 else "MOMENTUM" if psi < 0.10 else "REGIME CHANGE"
        prev_price = last_metadata.get("prev_price", "N/A")
        
        prompt = f"""### MARKET DATA SNAPSHOT
FRESH SYNTHETIC EV: ${synthesis.get('implied_price', 'N/A')}
PREVIOUS ESTIMATE: ${prev_price}
PROBABILITY SHIFT INDEX (PSI): {psi:.4f}
REQUIRED REGIME: {regime}
TOTAL EVENT VOLUME: ${synthesis.get('total_volume', 0):,}
ARBITRAGE DETECTED: {synthesis.get('arbitrage_detected', False)}

### FULL MARKET DATA (JSON)
{json.dumps(data, indent=2)}"""

        # Inject news RAG context if available
        news = data.get("news_context", [])
        if news:
            prompt += "\n\n### LIVE NEWS CONTEXT (RAG — use to explain the 'insight')\n"
            for i, headline in enumerate(news[:5], 1):
                prompt += f"{i}. {headline}\n"

        return prompt
        
    @staticmethod
    def extract_price(text: str) -> Optional[float]:
        match = re.search(r'\$([0-9,]+)', text)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except:
                pass
        return None

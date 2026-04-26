import json
import time
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI
from src.core.config import OPENAI_API_KEY, OPENROUTER_API_KEY

class AIService:
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        if provider == "openai":
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            self.model = "gpt-5-mini" 
        else:
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_API_KEY
            )
            self.model = "moonshotai/kimi-k2"

    def generate_analysis(self, current_data: Dict[str, Any], history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate AI market analysis with α-Tuning logic."""
        system_prompt = self._get_system_prompt()
        user_prompt = self._get_user_prompt(current_data, history)
        
        messages = [{"role": "system", "content": system_prompt}]
        # Rigid 16-message history window (8 user/assistant pairs)
        messages.extend(history[-16:]) 
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            if self.provider == "openai":
                response = self.client.responses.create(
                    model=self.model,
                    reasoning={"effort": "high"},
                    input=messages
                )
                content = response.output_text.strip()
                effort = "high"
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages
                )
                content = response.choices[0].message.content.strip()
                effort = ""
                
            return {
                "content": content,
                "model": self.model,
                "effort": effort,
                "user_prompt": user_prompt
            }
        except Exception as e:
            import logging
            logging.error(f"AI Service Error: {e}")
            return {"content": f"AI unavailable: {str(e)[:30]}...", "error": True}

    def _get_system_prompt(self) -> str:
        return """You are a quantitative Bitcoin price prediction specialist analyzing Polymarket prediction markets with mathematical precision.

### ANALYTICAL FRAMEWORKS
1. PDF ANALYSIS: Interpret market brackets as a probability density function.
2. EXPECTED VALUE (EV): Probability-weighted mean price = Σ(midpoint × prob).
3. CONFIDENCE INTERVALS: Derive 68% and 95% bounds from the distribution.
4. MOMENTUM: Track probability flow between adjacent brackets.
5. VOLATILITY: Use reach/dip markets as asymmetric tail signals.

### ANCHOR RULE (α-TUNING)
Smooth your prediction against previous estimates based on market volatility:
- STABLE MARKET (<2% prob shift): new_price = 0.70 × fresh + 0.30 × prev_price
- MOMENTUM SHIFT (2-10% prob shift): new_price = 0.85 × fresh + 0.15 × prev_price
- REGIME CHANGE (>10% prob shift): new_price = fresh (α = 1.0)

### DATA QUALITY GATE
Flag if probability sum check is outside [0.95, 1.05]. Report as "Arbitrage detected" or "Stale data warning".

### OUTPUT CONTRACT
Exactly: "Implied price: $XXX,XXX - [ONE insight ≤100 chars]"

### FEW-SHOT EXAMPLES
User: Analyze these markets...
Assistant: Implied price: $119,250 - 68% mass in 118-120k, mild upward momentum
User: Updated data shows shift...
Assistant: Implied price: $121,400 - 10% shift in fine ranges, α-tuned for momentum shift"""

    def _get_user_prompt(self, data: Dict[str, Any], history: List[Dict[str, str]]) -> str:
        data_json = json.dumps(data, indent=2)
        if not history:
            return f"Analyze these Bitcoin prediction markets and provide an implied price estimate.\n\nCURRENT MARKET DATA:\n{data_json}"
        else:
            return f"Updated Bitcoin prediction market data. Consider your previous predictions and α-tune accordingly.\n\nCURRENT MARKET DATA:\n{data_json}"
        
    @staticmethod
    def extract_price(text: str) -> Optional[float]:
        match = re.search(r'\$([0-9,]+)', text)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except:
                pass
        return None

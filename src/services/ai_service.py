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

    def generate_analysis(self, current_data: Dict[str, Any], history: List[Dict[str, str]], last_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI market analysis with deterministic α-Tuning integration."""
        system_prompt = self._get_system_prompt()
        user_prompt = self._get_user_prompt(current_data, last_metadata)
        
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
                
            content = content.replace('$', '').replace(',', '')
            price_match = re.search(r'price: ([0-9]+)', content.lower())
            
            # Move Cap Enforcement
            if price_match and last_metadata.get("prev_price"):
                new_p = float(price_match.group(1))
                prev_p = last_metadata["prev_price"]
                psi = current_data.get("mathematical_synthesis", {}).get("psi", 0.0)
                
                # Determine regime and cap
                cap = 800 if psi < 0.02 else 1500 if psi < 0.10 else float('inf')
                
                if abs(new_p - prev_p) > cap:
                    clamped_p = prev_p + (cap if new_p > prev_p else -cap)
                    content = content.replace(f"${int(new_p):,}", f"${int(clamped_p):,}")
                    content += f" [Clamped: PSI={psi:.3f}]"

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
Your primary objective is to synthesize multiple probability sources into a single implied price while maintaining consistency via α-Tuning.

### ALPHA-TUNING REGIMES (DETERMINISTIC)
You will be provided with a Probability Shift Index (PSI). Follow the assigned regime:
1. STABLE (PSI < 0.02): α = 0.70. Anchor heavily to history. Move limit: $800.
2. MOMENTUM (PSI 0.02 - 0.10): α = 0.85. Follow fresh data. Move limit: $1,500.
3. REGIME CHANGE (PSI > 0.10): α = 1.00. Market reset. No move limit.

### ANALYTICAL PRIORITIES
1. Trust Hierarchy: Fine Ranges (36060) have 40% weight.
2. Arbitrage: Flag if `arbitrage_detected` is True (e.g., Reach prob > Range prob).
3. Liquidity: Factor in `total_volume`. Low volume (<$10k) reduces signal reliability.
4. Skew: Use Reach/Dip markets (Tail Risk) to adjust the EV. 

### OUTPUT CONTRACT
Exactly: "Implied price: $XXX,XXX - [ONE insight ≤100 chars]"
No conversational filler. No yapping."""

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

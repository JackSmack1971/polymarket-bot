import json
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from src.core.config import OPENAI_API_KEY, OPENROUTER_API_KEY

class AIService:
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        if provider == "openai":
            self.client = OpenAI(api_key=OPENAI_API_KEY)
            self.model = "gpt-5-mini" # Example placeholder
        else:
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_API_KEY
            )
            self.model = "moonshotai/kimi-k2" # Example placeholder

    def generate_analysis(self, current_data: Dict[str, Any], history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate AI market analysis."""
        system_prompt = self._get_system_prompt()
        user_prompt = self._get_user_prompt(current_data, history)
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history[-16:]) # Cap history
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
            return {"content": f"AI Error: {str(e)[:40]}...", "error": True}

    def _get_system_prompt(self) -> str:
        return """You are a quantitative Bitcoin price prediction specialist.
        Output format: "Implied price: $XXX,XXX - [ONE key insight, max 100 chars]" """

    def _get_user_prompt(self, data: Dict[str, Any], history: List[Dict[str, str]]) -> str:
        return f"Analyze market data: {json.dumps(data)}"
        
    @staticmethod
    def extract_price(text: str) -> Optional[float]:
        import re
        match = re.search(r'\$([0-9,]+)', text)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except:
                pass
        return None

import json
from src.repositories.base_api import BaseAPI
from src.core.config import GAMMA_BASE, CLOB_BASE

class PolymarketRepository(BaseAPI):
    @classmethod
    def fetch_event_markets(cls, event_id: int):
        """Return list of brackets with yes/no token IDs and volume metadata."""
        url = f"{GAMMA_BASE}/events/{event_id}"
        ev = cls.http_get_json(url)
        if not ev or "markets" not in ev:
            return []
            
        rows = []
        for m in ev["markets"]:
            try:
                tokens = json.loads(m.get("clobTokenIds", "[]"))
                prices = json.loads(m.get("outcomePrices", "[]"))
                outcomes = json.loads(m.get("outcomes", "[]"))
            except Exception:
                continue
                
            if len(tokens) != 2 or outcomes != ["Yes", "No"]:
                continue
                
            q = m.get("question", "")
            rows.append({
                "bracket": q,
                "yes_token": tokens[0],
                "no_token": tokens[1],
                "yes_price": float(prices[0]) if prices else None,
                "no_price": float(prices[1]) if prices else None,
                "volume": float(m.get("volume", 0.0)),
                "liquidity": float(m.get("liquidity", 0.0)),
                "end_date": m.get("endDate")
            })
            
        # Keep a logical order: <120k, 120-121k, ..., >123k
        def keyer(q):
            s = q["bracket"].lower()
            if "less than" in s:
                return (0, s)
            if "between" in s:
                return (1, s)
            if "greater than" in s:
                return (2, s)
            return (9, s)
            
        rows.sort(key=keyer)
        return rows

    @classmethod
    def fetch_price(cls, token_id: str, side: str = "buy"):
        """Return executable price from CLOB."""
        url = f"{CLOB_BASE}/price?token_id={token_id}&side={side}"
        j = cls.http_get_json(url)
        if j is None:
            return None
        if isinstance(j, dict):
            return float(j.get("price")) if j.get("price") is not None else None
        if isinstance(j, (int, float)):
            return float(j)
        return None

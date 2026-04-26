from typing import List, Dict, Any, Optional
from src.repositories.polymarket import PolymarketRepository
from src.core.config import EVENT_ID_FINE_RANGES, EVENT_ID_REACH_DIP

class PredictionService:
    @staticmethod
    def calculate_implied_price(brackets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Calculate implied Bitcoin price from market probabilities."""
        try:
            # Get additional fine-grained data
            fine_ranges = PolymarketRepository.fetch_event_markets(EVENT_ID_FINE_RANGES)
            reach_dip_data = PolymarketRepository.fetch_event_markets(EVENT_ID_REACH_DIP)
            
            ranges = []
            prob_sum_check = 0.0
            
            # 1. Main Event (Broad Ranges - 35% Trust)
            for b in brackets:
                if b.get("last_yes") is None: continue
                bracket = b["bracket"].lower()
                prob = b["last_yes"]
                
                # Full mapping for 37049
                if "less than" in bracket and "120" in bracket:
                    ranges.append({"mid": 115000, "prob": prob, "source": "main", "weight": 0.35})
                elif "120" in bracket and "121" in bracket:
                    ranges.append({"mid": 120500, "prob": prob, "source": "main", "weight": 0.35})
                elif "121" in bracket and "122" in bracket:
                    ranges.append({"mid": 121500, "prob": prob, "source": "main", "weight": 0.35})
                elif "122" in bracket and "123" in bracket:
                    ranges.append({"mid": 122500, "prob": prob, "source": "main", "weight": 0.35})
                elif "greater than" in bracket and "123" in bracket:
                    ranges.append({"mid": 125000, "prob": prob, "source": "main", "weight": 0.35})
                
                if any(x in bracket for x in ["less than", "between", "greater than"]):
                    prob_sum_check += prob

            # 2. Fine Ranges (36060 - 40% Trust)
            for f in fine_ranges:
                bracket = f["bracket"].lower()
                prob = f["yes_price"]
                if prob is None: continue
                
                # Exhaustive mapping for 36060
                if "less than" in bracket and "110" in bracket:
                    ranges.append({"mid": 105000, "prob": prob, "source": "fine", "weight": 0.40})
                elif "110" in bracket and "112" in bracket:
                    ranges.append({"mid": 111000, "prob": prob, "source": "fine", "weight": 0.40})
                elif "112" in bracket and "114" in bracket:
                    ranges.append({"mid": 113000, "prob": prob, "source": "fine", "weight": 0.40})
                elif "114" in bracket and "116" in bracket:
                    ranges.append({"mid": 115000, "prob": prob, "source": "fine", "weight": 0.40})
                elif "116" in bracket and "118" in bracket:
                    ranges.append({"mid": 117000, "prob": prob, "source": "fine", "weight": 0.40})
                elif "greater than" in bracket and "118" in bracket:
                    ranges.append({"mid": 120000, "prob": prob, "source": "fine", "weight": 0.40})

            # 3. Reach/Dip (37057 - 25% Trust)
            for r in reach_dip_data:
                bracket = r["bracket"].lower()
                prob = r["yes_price"]
                if prob is None: continue
                if "dip to $120k" in bracket: continue # Resolved
                
                # Exhaustive mapping for 37057
                if "reach" in bracket and "$127k" in bracket:
                    ranges.append({"mid": 127000, "prob": prob, "source": "tail", "weight": 0.25})
                elif "reach" in bracket and "$125k" in bracket:
                    ranges.append({"mid": 125000, "prob": prob, "source": "tail", "weight": 0.25})
                elif "reach" in bracket and "$123k" in bracket:
                    ranges.append({"mid": 123000, "prob": prob, "source": "tail", "weight": 0.25})
                elif "dip to" in bracket and "$118k" in bracket:
                    ranges.append({"mid": 118000, "prob": prob, "source": "tail", "weight": 0.25})
                elif "dip to" in bracket and "$116k" in bracket:
                    ranges.append({"mid": 116000, "prob": prob, "source": "tail", "weight": 0.25})

            if not ranges:
                return None
                
            # Calculate standard EV
            total_weighted = sum(r["prob"] * r["mid"] for r in ranges)
            total_prob = sum(r["prob"] for r in ranges)
            implied_price = total_weighted / total_prob if total_prob > 0 else None
            
            # Identify most likely range
            max_prob_range = max(ranges, key=lambda x: x["prob"]) if ranges else None
            
            return {
                "implied_price": round(implied_price) if implied_price else None,
                "max_prob": round(max_prob_range["prob"], 3) if max_prob_range else 0.0,
                "max_prob_source": max_prob_range["source"] if max_prob_range else "unknown",
                "prob_sum_check": round(prob_sum_check, 4),
                "is_stable": 0.95 <= prob_sum_check <= 1.05,
                "trust_distribution": {
                    "fine": len([r for r in ranges if r["source"] == "fine"]),
                    "main": len([r for r in ranges if r["source"] == "main"]),
                    "tail": len([r for r in ranges if r["source"] == "tail"])
                }
            }
        except Exception:
            pass
        return None

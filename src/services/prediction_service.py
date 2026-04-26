from typing import List, Dict, Any, Optional
from src.repositories.polymarket import PolymarketRepository
from src.core.config import EVENT_ID_FINE_RANGES, EVENT_ID_REACH_DIP

class PredictionService:
    @staticmethod
    def calculate_implied_price(
        main_brackets: List[Dict[str, Any]], 
        fine_ranges: List[Dict[str, Any]], 
        reach_dip_data: List[Dict[str, Any]],
        previous_probs: Optional[Dict[str, float]] = None
    ) -> Optional[Dict[str, Any]]:
        """Calculate implied Bitcoin price from market probabilities with source weighting and arbitrage detection."""
        try:
            sources = {
                "main": {"data": main_brackets, "weight": 0.35, "ev": 0.0, "total_prob": 0.0, "total_vol": 0.0},
                "fine": {"data": fine_ranges, "weight": 0.40, "ev": 0.0, "total_prob": 0.0, "total_vol": 0.0},
                "tail": {"data": reach_dip_data, "weight": 0.25, "ev": 0.0, "total_prob": 0.0, "total_vol": 0.0}
            }
            
            all_ranges = []
            current_probs = {}

            # 1. Process Main Event
            for b in main_brackets:
                prob = b.get("last_yes", 0.0) or 0.0
                bracket = b["bracket"].lower()
                current_probs[b["bracket"]] = prob
                vol = b.get("volume", 0.0)
                
                mid = None
                if "less than" in bracket and "120" in bracket: mid = 115000
                elif "120" in bracket and "121" in bracket: mid = 120500
                elif "121" in bracket and "122" in bracket: mid = 121500
                elif "122" in bracket and "123" in bracket: mid = 122500
                elif "greater than" in bracket and "123" in bracket: mid = 125000
                
                if mid:
                    sources["main"]["ev"] += prob * mid
                    sources["main"]["total_prob"] += prob
                    sources["main"]["total_vol"] += vol
                    all_ranges.append({"mid": mid, "prob": prob, "source": "main", "vol": vol})

            # 2. Process Fine Ranges
            for f in fine_ranges:
                prob = f.get("last_yes", 0.0) or f.get("yes_price", 0.0) or 0.0
                bracket = f["bracket"].lower()
                current_probs[f["bracket"]] = prob
                vol = f.get("volume", 0.0)
                
                mid = None
                if "less than" in bracket and "110" in bracket: mid = 105000
                elif "110" in bracket and "112" in bracket: mid = 111000
                elif "112" in bracket and "114" in bracket: mid = 113000
                elif "114" in bracket and "116" in bracket: mid = 115000
                elif "116" in bracket and "118" in bracket: mid = 117000
                elif "greater than" in bracket and "118" in bracket: mid = 120000
                
                if mid:
                    sources["fine"]["ev"] += prob * mid
                    sources["fine"]["total_prob"] += prob
                    sources["fine"]["total_vol"] += vol
                    all_ranges.append({"mid": mid, "prob": prob, "source": "fine", "vol": vol})

            # 3. Process Reach/Dip
            for r in reach_dip_data:
                prob = r.get("last_yes", 0.0) or r.get("yes_price", 0.0) or 0.0
                bracket = r["bracket"].lower()
                current_probs[r["bracket"]] = prob
                vol = r.get("volume", 0.0)
                
                mid = None
                if "reach" in bracket and "$127k" in bracket: mid = 127000
                elif "reach" in bracket and "$125k" in bracket: mid = 125000
                elif "reach" in bracket and "$123k" in bracket: mid = 123000
                elif "dip to" in bracket and "$118k" in bracket: mid = 118000
                elif "dip to" in bracket and "$116k" in bracket: mid = 116000
                
                if mid:
                    sources["tail"]["ev"] += prob * mid
                    sources["tail"]["total_prob"] += prob
                    sources["tail"]["total_vol"] += vol
                    all_ranges.append({"mid": mid, "prob": prob, "source": "tail", "vol": vol})

            # Calculate Normalized EVs and Combined EV
            weighted_ev_sum = 0.0
            total_weight = 0.0
            total_volume = sum(s["total_vol"] for s in sources.values())
            
            source_evs = {}
            for name, s in sources.items():
                if s["total_prob"] > 0:
                    normalized_ev = s["ev"] / s["total_prob"]
                    source_evs[name] = normalized_ev
                    weighted_ev_sum += normalized_ev * s["weight"]
                    total_weight += s["weight"]
            
            implied_price = weighted_ev_sum / total_weight if total_weight > 0 else None
            
            # Calculate PSI (Probability Shift Index)
            psi = 0.0
            if previous_probs:
                for b, p in current_probs.items():
                    if b in previous_probs:
                        psi += abs(p - previous_probs[b])
            
            # Discrepancy Calculation
            discrepancy = round(abs(source_evs.get("fine", 0) - source_evs.get("main", 0))) if "fine" in source_evs and "main" in source_evs else 0

            # Arbitrage Logic: Probability check for contradictory outcomes
            arbitrage_detected = False
            # Example: Prob of 'Reach 125k' shouldn't be higher than 'Greater than 123k' by much
            reach_125 = current_probs.get("Bitcoin reach $125k before November 8?", 0.0)
            gt_123 = current_probs.get("Will the price of Bitcoin be greater than $123k on November 7?", 0.0)
            if reach_125 > gt_123 + 0.15: # 15% leeway for time difference
                arbitrage_detected = True

            # Calculate confidence score (0.0 to 1.0)
            conf = 1.0
            if psi > 0.10: conf -= 0.3 
            if discrepancy > 2000: conf -= 0.25 
            if total_volume < 10000: conf -= 0.15 # Low liquidity discount
            if not (0.95 <= sources["main"]["total_prob"] <= 1.05): conf -= 0.2
            conf = max(0.05, conf)

            # Identify most likely range
            max_prob_range = max(all_ranges, key=lambda x: x["prob"]) if all_ranges else None
            
            return {
                "implied_price": round(implied_price) if implied_price else None,
                "max_prob": round(max_prob_range["prob"], 3) if max_prob_range else 0.0,
                "max_prob_source": max_prob_range["source"] if max_prob_range else "unknown",
                "prob_sum_check": round(sources["main"]["total_prob"], 4),
                "is_stable": 0.95 <= sources["main"]["total_prob"] <= 1.05,
                "psi": round(psi, 4),
                "confidence_score": round(conf, 2),
                "discrepancy": discrepancy,
                "arbitrage_detected": arbitrage_detected,
                "total_volume": round(total_volume),
                "source_evs": {k: round(v) for k, v in source_evs.items()},
                "current_probs": current_probs
            }
        except Exception:
            import traceback
            traceback.print_exc()
        return None

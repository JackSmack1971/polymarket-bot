from typing import List, Tuple

SPARK_LEVELS = "▁▂▃▄▅▆▇█"

class SparklineGenerator:
    @staticmethod
    def get_segments(values: List[float], width: int = 12) -> List[Tuple[str, int]]:
        """Return list of (char, delta) for the last `width` samples."""
        if not values: return []
        
        vals = values[-width:]
        lo, hi = min(vals), max(vals)
        segs = []
        
        for i, v in enumerate(vals):
            t = 0 if hi == lo else (v - lo) / (hi - lo)
            idx = min(len(SPARK_LEVELS)-1, max(0, int(t*(len(SPARK_LEVELS)-1))))
            ch = SPARK_LEVELS[idx]
            
            if i == 0:
                delta = 0
            else:
                prev = vals[i-1]
                eps = 1e-6
                if v > prev + eps: delta = +1
                elif v < prev - eps: delta = -1
                else: delta = 0
            segs.append((ch, delta))
        return segs

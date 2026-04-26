import curses
from typing import List, Dict, Any

class HistogramRenderer:
    @staticmethod
    def draw_probability_dist(stdscr, row, col, width, height, brackets):
        """Draw a vertical histogram of probabilities."""
        if not brackets: return
        
        # Max probability for scaling
        max_p = max((b.get("last_yes", 0.0) or 0.0) for b in brackets)
        if max_p == 0: max_p = 1.0
        
        num_brackets = len(brackets)
        bar_w = max(1, (width - (num_brackets - 1)) // num_brackets)
        
        for i, b in enumerate(brackets):
            prob = b.get("last_yes", 0.0) or 0.0
            bar_h = int((prob / max_p) * height)
            
            x = col + i * (bar_w + 1)
            for h in range(bar_h):
                try:
                    # Color based on probability intensity
                    color = curses.color_pair(5 if prob > 0.5 else 3 if prob > 0.2 else 7)
                    stdscr.addstr(row + height - 1 - h, x, "█" * bar_w, color)
                except curses.error: pass

import curses
from typing import List, Optional

class ChartRenderer:
    @staticmethod
    def draw_price_chart(stdscr, start_row, start_col, width, height, ai_prices, btc_prices):
        """Draw a high-density Bloomberg-style price comparison chart."""
        if not ai_prices and not btc_prices:
            return

        # 1. Scaling Math
        all_p = [p for p in ai_prices + btc_prices if p]
        if not all_p: return
        
        min_p, max_p = min(all_p), max(all_p)
        if min_p == max_p:
            min_p -= 100; max_p += 100

        plot_w = width - 4
        plot_h = height - 6
        
        # 2. Draw Frame
        try:
            stdscr.addstr(start_row, start_col, "┌" + "─" * (width-2) + "┐", curses.color_pair(4))
            stdscr.addstr(start_row + 1, start_col, f"│ MAX: ${max_p:,.0f}".ljust(width-1) + "│")
            stdscr.addstr(start_row + height - 2, start_col, f"│ MIN: ${min_p:,.0f}".ljust(width-1) + "│")
            stdscr.addstr(start_row + height - 1, start_col, "└" + "─" * (width-2) + "┘", curses.color_pair(4))
        except curses.error: pass

        # 3. Plot Data (Horizontal Packing Factor: 0.5)
        # This allows 2 points per column for higher density
        
        def get_coords(price, index, total_count):
            if not price: return None, None
            # Horizontal packing logic
            x = start_col + 2 + int(index * (plot_w / max(1, total_count-1)) * 0.5)
            # Vertical scaling logic
            y_ratio = (price - min_p) / (max_p - min_p)
            y = start_row + 3 + int((1 - y_ratio) * plot_h)
            return x, y

        # AI Series (Yellow dots)
        max_len = max(len(ai_prices), len(btc_prices))
        for i, p in enumerate(ai_prices):
            x, y = get_coords(p, i, max_len)
            if x and y and x < start_col + width - 2 and y < start_row + height - 2:
                try: stdscr.addstr(y, x, "●", curses.color_pair(3) | curses.A_BOLD)
                except curses.error: pass

        # BTC Series (Green squares)
        for i, p in enumerate(btc_prices):
            x, y = get_coords(p, i, max_len)
            if x and y and x + 1 < start_col + width - 2 and y < start_row + height - 2:
                try: stdscr.addstr(y, x + 1, "■", curses.color_pair(1) | curses.A_BOLD)
                except curses.error: pass

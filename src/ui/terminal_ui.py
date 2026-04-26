import curses
import time
import threading
from typing import Dict, Any, List
import copy
import logging
from src.core.state_manager import StateManager
from src.core.orchestrator import ThreadOrchestrator
from src.ui.charts import ChartRenderer
from src.ui.sparklines import SparklineGenerator
from src.ui.histogram import HistogramRenderer

class TerminalUI:
    def __init__(self, event_id: int, provider: str, interval: int):
        self.event_id = event_id
        self.interval = interval
        self.state = StateManager()
        self.orchestrator = ThreadOrchestrator(self.state, event_id, provider)
        self.running = True

    def start(self):
        self.orchestrator.start()
        try:
            curses.wrapper(self._main_loop)
        finally:
            self.orchestrator.stop()

    def _main_loop(self, stdscr):
        self._init_curses(stdscr)
        
        while self.running:
            h, w = stdscr.getmaxyx()
            
            # Rendering is now independent of data ingestion
            self._render(stdscr, h, w)
            
            stdscr.timeout(self.interval * 1000)
            ch = stdscr.getch()
            if ch in (ord('q'), ord('Q'), 27):
                self.running = False

    def _init_curses(self, stdscr):
        curses.curs_set(0)
        curses.use_default_colors()
        # 1-3: Directions/Confidence
        curses.init_pair(1, curses.COLOR_GREEN, -1)  # UP / HIGH
        curses.init_pair(2, curses.COLOR_RED, -1)    # DOWN / LOW
        curses.init_pair(3, curses.COLOR_YELLOW, -1) # FLAT / MED
        # 4: Borders/Headings
        curses.init_pair(4, curses.COLOR_CYAN, -1)
        # 5-7: Sparklines
        curses.init_pair(5, curses.COLOR_GREEN, -1)
        curses.init_pair(6, curses.COLOR_RED, -1)
        curses.init_pair(7, -1, -1) # Default
        # 8: Chart Lines
        curses.init_pair(8, curses.COLOR_MAGENTA, -1)

    def _render(self, stdscr, h, w):
        stdscr.erase()
        
        # 0. Get Data Snapshots
        with self.state.market.lock:
            brackets = copy.deepcopy(self.state.market.main_brackets)
            last_mkt_update = self.state.market.last_update
        
        # 1. Header
        tstamp = time.strftime("%H:%M:%S UTC", time.gmtime())
        header = f"▓▓▓ POLYMARKET TERMINAL ▓▓▓  E:{self.event_id}  {tstamp}  [q: quit]"
        try:
            stdscr.addstr(0, 0, header[:w-1], curses.color_pair(4) | curses.A_BOLD)
        except curses.error: pass

        # Layout constants
        sep_col = min(72, w * 5 // 8)
        ai_w = sep_col - 2

        # Check if we have data
        if not brackets:
            try:
                stdscr.addstr(h//2, (sep_col - 10)//2, "LOADING DATA...", curses.A_REVERSE | curses.A_BOLD)
            except curses.error: pass
        else:
            # 2. AI Analysis Panel (Top Left)
            with self.state.ai.lock:
                analysis_text = self.state.ai.analysis
                model_info = self.state.ai.model
                effort = self.state.ai.effort
                ai_lines = self._wrap_text(analysis_text, ai_w, model_info, effort)
            
            for i, line in enumerate(ai_lines):
                if 1 + i >= h - 1: break
                try:
                    # Highlight the prefix
                    if "> " in line:
                        prefix, rest = line.split("> ", 1)
                        stdscr.addstr(1 + i, 0, prefix + "> ", curses.color_pair(1) | curses.A_BOLD)
                        stdscr.addstr(1 + i, len(prefix) + 2, rest[:ai_w - len(prefix) - 2], curses.color_pair(3) | curses.A_ITALIC)
                    else:
                        stdscr.addstr(1 + i, 0, line[:ai_w], curses.color_pair(3) | curses.A_ITALIC)
                except curses.error: pass

            # 2.5 Probability Distribution
            hist_h = 4
            hist_y = 1 + len(ai_lines) + 1
            if hist_y + hist_h < h - 2:
                HistogramRenderer.draw_probability_dist(stdscr, hist_y, 0, ai_w, hist_h, brackets)

            # 3. Market Data Panel (Bottom Left)
            table_start_row = hist_y + hist_h + 1
            if table_start_row < h - 5:
                try:
                    stdscr.addstr(table_start_row, 0, "BRACKET".ljust(25) + "YES".ljust(10) + "DIR".ljust(5) + "TREND", curses.color_pair(4) | curses.A_UNDERLINE)
                    stdscr.hline(table_start_row + 1, 0, ord('─'), sep_col - 1)
                except curses.error: pass

                for i, b in enumerate(brackets):
                    row = table_start_row + 2 + i
                    if row >= h - 2: break
                    
                    yp = b.get("last_yes", 0.0) or 0.0
                    hist = b.get("yes_hist", [])

                    # Label
                    label = b["bracket"].replace("Will the price of Bitcoin be ", "")[:24]
                    try:
                        stdscr.addstr(row, 0, label.ljust(25))
                        stdscr.addstr(row, 25, f"{yp:.3f}".ljust(10))
                        
                        # Sparkline
                        if hist:
                            segs = SparklineGenerator.get_segments(hist, width=15)
                            for j, (ch, delta) in enumerate(segs):
                                color = curses.color_pair(5 if delta > 0 else 6 if delta < 0 else 7)
                                stdscr.addstr(row, 40 + j, ch, color)
                    except curses.error: pass

        # 4. Vertical Separator
        for r in range(1, h-1):
            try: stdscr.addstr(r, sep_col, "│", curses.color_pair(4))
            except curses.error: pass

        # 5. Chart Panel (Right)
        if w > 95:
            ai_hist, btc_hist = self.state.get_histories()
            ChartRenderer.draw_price_chart(stdscr, 1, sep_col + 2, w - sep_col - 3, h - 3, ai_hist, btc_hist)

        # 6. Footer (BTC Price & Thread Status)
        with self.state.btc.lock:
            btc_price = self.state.btc.price
            last_btc_update = self.state.btc.last_update
        
        status_line = ""
        if btc_price:
            status_line += f"BTC: ${btc_price:,.0f} "
        
        # Thread health
        now = time.time()
        
        def get_status(last_upd, interval, name):
            if last_upd == 0: return f"{name}: WAIT"
            diff = now - last_upd
            if diff > interval * 2.5: return f"{name}: LAG"
            return f"{name}: OK"

        with self.state.ai.lock:
            ai_status = get_status(self.state.ai.last_update, 30, "AI")
            conf = self.state.ai.confidence_score
        
        mkt_status = get_status(last_mkt_update, 15, "MKT")
        btc_status = get_status(last_btc_update, 60, "CG")
        
        # Confidence Indicator
        if conf > 0.8:
            conf_str = f"CONF: {int(conf*100)}% [HIGH]"
            color = curses.color_pair(1)
        elif conf > 0.5:
            conf_str = f"CONF: {int(conf*100)}% [MED]"
            color = curses.color_pair(3)
        else:
            conf_str = f"CONF: {int(conf*100)}% [LOW]"
            color = curses.color_pair(2)
        
        full_footer = f"{status_line} │ {ai_status} │ {mkt_status} │ {btc_status} │ {conf_str}"
        try: 
            stdscr.addstr(h-1, 0, full_footer[:w-1], color | curses.A_BOLD)
        except curses.error: pass

        stdscr.refresh()

    def _wrap_text(self, text, width, model, effort):
        prefix = f"[{model}{'-'+effort if effort else ''}]> "
        words = text.split()
        lines = []
        cur = prefix
        for w in words:
            if len(cur + w) + 1 <= width:
                cur += (w if cur == prefix else " " + w)
            else:
                lines.append(cur)
                cur = "    " + w
        if cur: lines.append(cur)
        return lines

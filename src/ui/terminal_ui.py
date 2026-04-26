import curses
import time
import threading
from typing import Dict, Any, List
import copy
from src.core.state_manager import StateManager
from src.repositories.polymarket import PolymarketRepository
from src.repositories.coingecko import CoinGeckoRepository
from src.services.prediction_service import PredictionService
from src.services.ai_service import AIService
from src.ui.charts import ChartRenderer
from src.ui.sparklines import SparklineGenerator
from src.core.config import EVENT_ID_FINE_RANGES, EVENT_ID_REACH_DIP

class TerminalUI:
    def __init__(self, event_id: int, provider: str, interval: int):
        self.event_id = event_id
        self.interval = interval
        self.state = StateManager()
        self.ai_service = AIService(provider)
        self.running = True

    def start(self):
        curses.wrapper(self._main_loop)

    def _main_loop(self, stdscr):
        self._init_curses(stdscr)
        
        # Initial data load into state
        main_brackets = PolymarketRepository.fetch_event_markets(self.event_id)
        for b in main_brackets:
            b["yes_hist"] = []
            b["last_yes"] = None
        
        with self.state.market.lock:
            self.state.market.main_brackets = main_brackets
            # Fetch secondary event structures too
            self.state.market.fine_brackets = PolymarketRepository.fetch_event_markets(EVENT_ID_FINE_RANGES)
            self.state.market.tail_brackets = PolymarketRepository.fetch_event_markets(EVENT_ID_REACH_DIP)

        while self.running:
            # Handle terminal resize
            h, w = stdscr.getmaxyx()
            
            self._update_background_threads()
            self._render(stdscr, h, w)
            
            stdscr.timeout(self.interval * 1000)
            ch = stdscr.getch()
            if ch in (ord('q'), ord('Q'), 27):
                self.running = False

    def _init_curses(self, stdscr):
        curses.curs_set(0)
        curses.use_default_colors()
        # 1-3: Directions
        curses.init_pair(1, curses.COLOR_GREEN, -1)  # UP
        curses.init_pair(2, curses.COLOR_RED, -1)    # DOWN
        curses.init_pair(3, curses.COLOR_YELLOW, -1) # FLAT
        # 4: Borders/Headings
        curses.init_pair(4, curses.COLOR_CYAN, -1)
        # 5-7: Sparklines
        curses.init_pair(5, curses.COLOR_GREEN, -1)
        curses.init_pair(6, curses.COLOR_RED, -1)
        curses.init_pair(7, -1, -1) # Default
        # 8: Chart Lines
        curses.init_pair(8, curses.COLOR_MAGENTA, -1)

    def _update_background_threads(self):
        # AI Update (every 30s)
        if not self.state.ai.updating and (time.time() - self.state.ai.last_update > 30):
            self.state.ai.updating = True
            threading.Thread(target=self._ai_worker, daemon=True, name="AIWorker").start()
            
        # BTC Update (every 60s)
        if not self.state.btc.updating and (time.time() - self.state.btc.last_update > 60):
            self.state.btc.updating = True
            threading.Thread(target=self._btc_worker, daemon=True, name="BTCWorker").start()

        # Market Update (every 15s)
        if not self.state.market.updating and (time.time() - self.state.market.last_update > 15):
            self.state.market.updating = True
            threading.Thread(target=self._market_worker, daemon=True, name="MarketWorker").start()

    def _market_worker(self):
        try:
            # Get a snapshot of token IDs to check
            with self.state.market.lock:
                all_tokens = []
                for brackets in [self.state.market.main_brackets, self.state.market.fine_brackets, self.state.market.tail_brackets]:
                    for b in brackets:
                        if b.get("yes_token"): all_tokens.append(b["yes_token"])
            
            new_prices = {}
            for tid in set(all_tokens):
                p = PolymarketRepository.fetch_price(tid)
                if p is not None:
                    new_prices[tid] = p
            
            with self.state.market.lock:
                self.state.market.price_map.update(new_prices)
                self.state.market.last_update = time.time()
                # Update last_yes in all brackets for easier access
                for brackets in [self.state.market.main_brackets, self.state.market.fine_brackets, self.state.market.tail_brackets]:
                    for b in brackets:
                        tid = b.get("yes_token")
                        if tid in self.state.market.price_map:
                            b["last_yes"] = self.state.market.price_map[tid]
        finally:
            with self.state.market.lock:
                self.state.market.updating = False

    def _ai_worker(self):
        try:
            # Take a thread-safe deep copy for analysis
            with self.state.market.lock:
                main = copy.deepcopy(self.state.market.main_brackets)
                fine = copy.deepcopy(self.state.market.fine_brackets)
                tail = copy.deepcopy(self.state.market.tail_brackets)

            synthesis = PredictionService.calculate_implied_price(main, fine, tail)
            market_data = {
                "main_event": main,
                "mathematical_synthesis": synthesis,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
            }
            result = self.ai_service.generate_analysis(market_data, self.state.ai.conversation_history)
            
            with self.state.ai.lock:
                self.state.ai.analysis = result["content"]
                self.state.ai.model = result.get("model", "AI")
                self.state.ai.effort = result.get("effort", "")
                self.state.ai.last_update = time.time()
                self.state.ai.conversation_history.append({"role": "user", "content": f"Analyze: {market_data.get('timestamp')}"})
                self.state.ai.conversation_history.append({"role": "assistant", "content": result["content"]})
                if len(self.state.ai.conversation_history) > 16:
                    self.state.ai.conversation_history = self.state.ai.conversation_history[-16:]
                price = AIService.extract_price(result["content"])
                if price: self.state.update_ai_history(price)
        finally:
            with self.state.ai.lock:
                self.state.ai.updating = False

    def _btc_worker(self):
        try:
            price = CoinGeckoRepository.fetch_btc_price()
            if price:
                with self.state.btc.lock:
                    self.state.btc.price = price
                    self.state.btc.last_update = time.time()
                self.state.update_btc_history(price)
        finally:
            with self.state.btc.lock:
                self.state.btc.updating = False

    def _render(self, stdscr, h, w):
        stdscr.erase()
        
        # 0. Get Data Snapshots
        with self.state.market.lock:
            brackets = copy.deepcopy(self.state.market.main_brackets)
        
        # 1. Header
        tstamp = time.strftime("%H:%M:%S UTC", time.gmtime())
        header = f"▓▓▓ POLYMARKET TERMINAL ▓▓▓  E:{self.event_id}  {tstamp}  [q: quit]"
        try:
            stdscr.addstr(0, 0, header[:w-1], curses.color_pair(4) | curses.A_BOLD)
        except curses.error: pass

        # Layout constants
        sep_col = min(72, w * 5 // 8)
        ai_w = sep_col - 2

        # 2. AI Analysis Panel (Top Left)
        with self.state.ai.lock:
            analysis_text = self.state.ai.analysis
            model_info = self.state.ai.model
            effort = self.state.ai.effort

        ai_lines = self._wrap_text(analysis_text, ai_w, model_info, effort)
        for i, line in enumerate(ai_lines):
            if 1 + i < h - 2:
                try:
                    # Color the model prefix
                    prefix_end = line.find(']> ') + 3 if ']> ' in line else 0
                    if prefix_end > 0:
                        stdscr.addstr(1+i, 0, line[:prefix_end], curses.color_pair(1) | curses.A_BOLD)
                        stdscr.addstr(1+i, prefix_end, line[prefix_end:], curses.color_pair(3) | curses.A_ITALIC)
                    else:
                        stdscr.addstr(1+i, 0, line, curses.color_pair(3) | curses.A_ITALIC)
                except curses.error: pass

        # 3. Market Data Panel (Bottom Left)
        table_start_row = 1 + len(ai_lines) + 1
        if table_start_row < h - 5:
            try:
                stdscr.addstr(table_start_row, 0, "BRACKET".ljust(25) + "YES".ljust(10) + "DIR".ljust(5) + "TREND", curses.color_pair(4))
                stdscr.hline(table_start_row + 1, 0, ord('─'), sep_col - 1)
            except curses.error: pass

            for i, b in enumerate(brackets):
                row = table_start_row + 2 + i
                if row >= h - 2: break
                
                # Price is already updated in b["last_yes"] by MarketWorker
                yp = b.get("last_yes", 0.0) or 0.0
                
                # Update history for sparkline (we need to persist this in the state's original brackets)
                with self.state.market.lock:
                    orig_b = self.state.market.main_brackets[i]
                    orig_b["yes_hist"].append(yp)
                    orig_b["yes_hist"] = orig_b["yes_hist"][-30:]
                    hist = list(orig_b["yes_hist"])

                # Label
                label = b["bracket"].replace("Will the price of Bitcoin be ", "")[:24]
                try:
                    stdscr.addstr(row, 0, label.ljust(25))
                    stdscr.addstr(row, 25, f"{yp:.3f}".ljust(10))
                    
                    # Sparkline
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
        
        status_line = ""
        # BTC
        if btc_price:
            status_line += f"BTC: ${btc_price:,.0f} "
        
        # Thread health
        now = time.time()
        
        def get_status(last_upd, interval, name):
            if last_upd == 0: return f"{name}: WAIT"
            diff = now - last_upd
            if diff > interval * 2: return f"{name}: LAGGING"
            return f"{name}: OK"

        ai_status = get_status(self.state.ai.last_update, 30, "AI")
        mkt_status = get_status(self.state.market.last_update, 15, "MKT")
        btc_status = get_status(self.state.btc.last_update, 60, "CG")
        
        full_footer = f"{status_line} │ {ai_status} │ {mkt_status} │ {btc_status}"
        try: 
            stdscr.addstr(h-1, 0, full_footer[:w-1], curses.color_pair(1) | curses.A_BOLD)
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

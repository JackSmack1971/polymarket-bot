import curses
import time
import threading
from typing import Dict, Any
from src.core.state_manager import StateManager
from src.repositories.polymarket import PolymarketRepository
from src.repositories.coingecko import CoinGeckoRepository
from src.services.prediction_service import PredictionService
from src.services.ai_service import AIService
from src.ui.charts import ChartRenderer
from src.ui.sparklines import SparklineGenerator

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
        
        # Initial data load
        brackets = PolymarketRepository.fetch_event_markets(self.event_id)
        for b in brackets:
            b["yes_hist"] = []
            b["last_yes"] = None

        while self.running:
            self._update_background_threads(brackets)
            self._render(stdscr, brackets)
            
            stdscr.timeout(self.interval * 1000)
            ch = stdscr.getch()
            if ch in (ord('q'), ord('Q'), 27):
                self.running = False

    def _init_curses(self, stdscr):
        curses.curs_set(0)
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_GREEN, -1)
        curses.init_pair(2, curses.COLOR_RED, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_CYAN, -1)

    def _update_background_threads(self, brackets):
        # AI Update
        if not self.state.ai.updating and (time.time() - self.state.ai.last_update > 30):
            self.state.ai.updating = True
            threading.Thread(target=self._ai_worker, args=(brackets,), daemon=True).start()
            
        # BTC Update
        if not self.state.btc.updating and (time.time() - self.state.btc.last_update > 60):
            self.state.btc.updating = True
            threading.Thread(target=self._btc_worker, daemon=True).start()

    def _ai_worker(self, brackets):
        try:
            # Format data for AI
            market_data = {"markets": brackets} # Simplified
            result = self.ai_service.generate_analysis(market_data, self.state.ai.conversation_history)
            
            with self.state.ai.lock:
                self.state.ai.analysis = result["content"]
                self.state.ai.model = result.get("model", "AI")
                self.state.ai.last_update = time.time()
                self.state.ai.conversation_history.append({"role": "assistant", "content": result["content"]})
                
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

    def _render(self, stdscr, brackets):
        h, w = stdscr.getmaxyx()
        stdscr.erase()
        
        # Header
        tstamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        header = f"▓▓▓ POLYMARKET TERMINAL ▓▓▓  Event {self.event_id}  {tstamp} [q: quit]"
        stdscr.addstr(0, 0, header[:w-1], curses.color_pair(4) | curses.A_BOLD)
        
        # Draw AI, Markets, and Chart...
        # (Complete render logic logic here)
        
        stdscr.refresh()

import threading
import time
import copy
import logging
from typing import Dict, Any, List, Optional
from src.core.state_manager import StateManager
from src.repositories.polymarket import PolymarketRepository
from src.repositories.coingecko import CoinGeckoRepository
from src.repositories.news import NewsRepository
from src.services.prediction_service import PredictionService
from src.services.ai_service import AIService
from src.services.evaluation_service import EvaluationService
from src.core.config import EVENT_ID_FINE_RANGES, EVENT_ID_REACH_DIP

class ThreadOrchestrator:
    def __init__(self, state: StateManager, event_id: int, provider: str):
        self.state = state
        self.event_id = event_id
        self.ai_service = AIService(provider)
        self.running = False
        self._threads: List[threading.Thread] = []

    def start(self):
        self.running = True
        # Perform initial market load in a separate thread to not block UI
        threading.Thread(target=self._initial_load, daemon=True, name="InitLoader").start()
        
        # Start main maintenance loop
        threading.Thread(target=self._orchestrator_loop, daemon=True, name="Orchestrator").start()
        logging.info("ThreadOrchestrator started.")

    def stop(self):
        self.running = False
        logging.info("ThreadOrchestrator stopping...")

    def _initial_load(self):
        while self.running:
            try:
                logging.info("Performing initial market load...")
                main_brackets = PolymarketRepository.fetch_event_markets(self.event_id)
                if not main_brackets:
                    raise ValueError("Main event markets empty")
                
                for b in main_brackets:
                    b["yes_hist"] = []
                    b["last_yes"] = None
                
                with self.state.market.lock:
                    self.state.market.main_brackets = main_brackets
                    self.state.market.fine_brackets = PolymarketRepository.fetch_event_markets(EVENT_ID_FINE_RANGES)
                    self.state.market.tail_brackets = PolymarketRepository.fetch_event_markets(EVENT_ID_REACH_DIP)
                    self.state.market.last_update = time.time()
                
                logging.info("Initial market load complete.")
                break # Exit loop on success
            except Exception as e:
                logging.error(f"Initial load failed: {e}. Retrying in 5s...")
                time.sleep(5)

    def _orchestrator_loop(self):
        while self.running:
            try:
                self._check_and_spawn_workers()
            except Exception as e:
                logging.error(f"Error in orchestrator loop: {e}", exc_info=True)
            time.sleep(1)

    def _check_and_spawn_workers(self):
        now = time.time()
        
        # Market Update (every 15s)
        if not self.state.market.updating and (now - self.state.market.last_update > 15):
            if self.state.market.main_brackets: # Only if initial load finished
                self.state.market.updating = True
                threading.Thread(target=self._market_worker, daemon=True, name="MarketWorker").start()

        # AI Update (every 30s)
        if not self.state.ai.updating and (now - self.state.ai.last_update > 30):
            if self.state.market.main_brackets:
                self.state.ai.updating = True
                threading.Thread(target=self._ai_worker, daemon=True, name="AIWorker").start()
            
        # BTC Update (every 60s)
        if not self.state.btc.updating and (now - self.state.btc.last_update > 60):
            self.state.btc.updating = True
            threading.Thread(target=self._btc_worker, daemon=True, name="BTCWorker").start()

        # News Update (every 300s)
        if not self.state.news.updating and (now - self.state.news.last_update > 300):
            self.state.news.updating = True
            threading.Thread(target=self._news_worker, daemon=True, name="NewsWorker").start()

    def _market_worker(self):
        try:
            # Snapshot token IDs
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
                for brackets in [self.state.market.main_brackets, self.state.market.fine_brackets, self.state.market.tail_brackets]:
                    for b in brackets:
                        tid = b.get("yes_token")
                        if tid in self.state.market.price_map:
                            yp = self.state.market.price_map[tid]
                            b["last_yes"] = yp
                            # Update history via state manager for thread safety and encapsulation
                            self.state.update_market_history(tid, yp)
        except Exception as e:
            logging.error(f"MarketWorker Error: {e}")
        finally:
            with self.state.market.lock:
                self.state.market.updating = False

    def _ai_worker(self):
        try:
            with self.state.market.lock:
                main = copy.deepcopy(self.state.market.main_brackets)
                fine = copy.deepcopy(self.state.market.fine_brackets)
                tail = copy.deepcopy(self.state.market.tail_brackets)
            
            with self.state.ai.lock:
                prev_meta = copy.deepcopy(self.state.ai.last_prediction_metadata)
                prev_probs = prev_meta.get("current_probs")

            synthesis = PredictionService.calculate_implied_price(main, fine, tail, previous_probs=prev_probs)
            if not synthesis: return

            market_data = {
                "main_event": main,
                "mathematical_synthesis": synthesis,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
            }
            # Inject latest news headlines into market data
            with self.state.news.lock:
                headlines = list(self.state.news.headlines)
            if headlines:
                market_data["news_context"] = headlines

            result = self.ai_service.generate_analysis(market_data, self.state.ai.conversation_history, prev_meta)

            implied_price = result.get("implied_price")
            # Fallback: try regex if structured output unavailable
            if not implied_price:
                implied_price = AIService.extract_price(result["content"])

            with self.state.ai.lock:
                self.state.ai.analysis = result["content"]
                self.state.ai.model = result.get("model", "AI")
                self.state.ai.internal_audit = result.get("internal_audit", "")
                self.state.ai.last_update = time.time()
                self.state.ai.conversation_history.append({"role": "user", "content": f"Analyze: {market_data.get('timestamp')}"})
                self.state.ai.conversation_history.append({"role": "assistant", "content": result["content"]})
                if len(self.state.ai.conversation_history) > 16:
                    self.state.ai.conversation_history = self.state.ai.conversation_history[-16:]

                self.state.ai.last_prediction_metadata = {
                    "prev_price": implied_price or prev_meta.get("prev_price"),
                    "current_probs": synthesis.get("current_probs")
                }
                self.state.ai.confidence_score = synthesis.get("confidence_score", 1.0)

                if implied_price:
                    self.state.update_ai_history(float(implied_price))

            # Log prediction to Performance Ledger
            if implied_price:
                EvaluationService.log_prediction(float(implied_price))
        except Exception as e:
            logging.error(f"AIWorker Error: {e}")
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
                # Record actual price for performance ledger comparison
                EvaluationService.log_actual_price(price)
        except Exception as e:
            logging.error(f"BTCWorker Error: {e}")
        finally:
            with self.state.btc.lock:
                self.state.btc.updating = False

    def _news_worker(self):
        try:
            headlines = NewsRepository.fetch_btc_headlines()
            with self.state.news.lock:
                self.state.news.headlines = headlines
                self.state.news.last_update = time.time()
            logging.info(f"NewsWorker: fetched {len(headlines)} headlines.")
        except Exception as e:
            logging.error(f"NewsWorker Error: {e}")
        finally:
            with self.state.news.lock:
                self.state.news.updating = False

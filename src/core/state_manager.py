import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class MarketState:
    current_data: Optional[Dict[str, Any]] = None
    price_map: Dict[str, float] = field(default_factory=dict)
    main_brackets: List[Dict[str, Any]] = field(default_factory=list)
    fine_brackets: List[Dict[str, Any]] = field(default_factory=list)
    tail_brackets: List[Dict[str, Any]] = field(default_factory=list)
    last_update: float = 0.0
    updating: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

@dataclass
class AIState:
    analysis: str = "Waiting for market data..."
    last_update: float = 0.0
    previous_data: Optional[Dict[str, Any]] = None
    updating: bool = False
    model: str = "AI"
    effort: str = ""
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

@dataclass
class BTCState:
    price: Optional[float] = None
    last_update: float = 0.0
    updating: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

class StateManager:
    def __init__(self):
        self.market = MarketState()
        self.ai = AIState()
        self.btc = BTCState()
        self.ai_price_history: List[float] = []
        self.btc_price_history: List[float] = []
        self.history_lock = threading.Lock()

    def update_ai_history(self, price: float):
        with self.history_lock:
            if not self.ai_price_history or abs(price - self.ai_price_history[-1]) > 0.01:
                self.ai_price_history.append(price)
                self.ai_price_history = self.ai_price_history[-100:]

    def update_btc_history(self, price: float):
        with self.history_lock:
            if not self.btc_price_history or abs(price - self.btc_price_history[-1]) > 0.01:
                self.btc_price_history.append(price)
                self.btc_price_history = self.btc_price_history[-100:]

    def get_histories(self):
        with self.history_lock:
            return list(self.ai_price_history), list(self.btc_price_history)

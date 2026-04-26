# Threading Lock Pattern (v3.0)

To prevent race conditions and ensure production stability, follow this pattern using the `StateManager` and its internal dataclass locks.

## 1. StateManager Initialization
```python
from src.core.state_manager import StateManager

state = StateManager()
# Access locks via:
# state.market.lock
# state.ai.lock
# state.btc.lock
```

## 2. Protected Worker Pattern
The `updating = False` flag must be reset in a `finally` block, and all writes must be wrapped in the specific lock.

```python
def _worker_method(self):
    """Background thread worker inside Orchestrator."""
    try:
        # 1. Fetch data (outside lock to avoid blocking UI)
        new_data = self.repository.fetch_data()
        
        # 2. Update state (inside lock)
        if new_data:
            with self.state.market.lock:
                self.state.market.current_data = new_data
                self.state.market.last_update = time.time()
                
    except Exception as e:
        logging.error(f"Worker Error: {e}")
    finally:
        # 3. Reset updating flag (MANDATORY in finally)
        with self.state.market.lock:
            self.state.market.updating = False
```

## 3. Safe Orchestrator Spawn
Gate the thread spawning in the maintenance loop.

```python
# Inside ThreadOrchestrator._check_and_spawn_workers()
if not self.state.market.updating and (now - self.state.market.last_update > 15):
    self.state.market.updating = True # Set flag before spawning
    threading.Thread(target=self._market_worker, daemon=True).start()
```

## 4. UI Thread Read
Always use the lock when reading attributes that might be partially written by the background thread.

```python
# Inside ui_engine.py
with state.ai.lock:
    current_analysis = state.ai.analysis
    model_name = state.ai.model
```


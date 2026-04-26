# Thread Patterns Reference

## Table of Contents
1. [Orchestrator Worker Template](#1-orchestrator-worker-template)
2. [Data Snapshotting (Deepcopy)](#2-data-snapshotting-deepcopy)
3. [Background Logging Pattern](#3-background-logging-pattern)
4. [Curses Thread Safety](#4-curses-thread-safety)

---

## 1. Orchestrator Worker Template

Every worker function must use a `finally` block and the appropriate `state.[category].lock`.

```python
def _ai_worker(self):
    try:
        # 1. Prepare data (Snapshotting)
        with self.state.market.lock:
            main = copy.deepcopy(self.state.market.main_brackets)
            
        # 2. Long running I/O (Outside lock)
        result = self.ai_service.generate_analysis(main)
        
        # 3. Update state (Inside lock)
        with self.state.ai.lock:
            self.state.ai.analysis = result["content"]
            self.state.ai.last_update = time.time()
            
    except Exception as e:
        logging.error(f"AIWorker Error: {e}")
    finally:
        # ALWAYS reset here, inside the thread
        with self.state.ai.lock:
            self.state.ai.updating = False
```

---

## 2. Data Snapshotting (Deepcopy)

Use `copy.deepcopy` when taking data from one state (e.g., Market) to use in another (e.g., AI Analysis) to prevent the AI service from reading data that changes mid-execution.

```python
with self.state.market.lock:
    # Snapshotting prevents race conditions during the 5-10s AI call
    main_snapshot = copy.deepcopy(self.state.market.main_brackets)
    fine_snapshot = copy.deepcopy(self.state.market.fine_brackets)
```

---

## 3. Background Logging Pattern

Since background threads don't output to the TUI terminal, use `logging` to capture errors.

```python
import logging
logging.basicConfig(filename='bot.log', level=logging.INFO)

# Inside worker
except Exception as e:
    logging.error(f"Worker Exception: {e}", exc_info=True)
```

---

## 4. Curses Thread Safety

**NEVER** draw from a background thread. Curses state is global and will crash if accessed concurrently.

```python
# RIGHT: Draw in the main thread loop
while True:
    draw_ui(stdscr, state) # Main thread only
    stdscr.refresh()
    key = stdscr.getch()

# WRONG: Do not do this
def _worker_method(self):
    stdscr.addstr(...) # CRASH
```


# Thread Patterns Reference

## Table of Contents
1. [Standard Async Function Template](#1-standard-async-function-template)
2. [Adding a New Thread (4th Source)](#2-adding-a-new-thread-4th-source)
3. [Binance Funding Rate Example](#3-binance-funding-rate-example)
4. [Lock-Safe State Wrapper](#4-lock-safe-state-wrapper)
5. [Graceful Degradation Pattern](#5-graceful-degradation-pattern)
6. [Laggy UI Fixes](#6-laggy-ui-fixes)

---

---

## 1. Standard Async Function Template

Every async function must use a `finally` block to ensure `updating = False` is reset even on failure.

```python
def update_source_async(state_dict):
    try:
        # Do I/O here
        result = fetch_data()
        state_dict['data'] = result
        state_dict['last_update'] = time.time()
    except Exception as e:
        state_dict['data'] = f"Error: {str(e)[:30]}"
    finally:
        # ALWAYS reset here, inside the thread
        state_dict['updating'] = False
```

---

## 2. Multi-Source Data Collection

The `market_state` thread collects data from three separate events simultaneously.

```python
def collect_market_data_async(brackets, event_id, market_state):
    try:
        # brackets list contains items from multiple event IDs:
        # main_event + additional_event + reach_dip_event
        current_data = format_market_data_for_ai(brackets, event_id)
        if current_data["markets"]:
            market_state['current_data'] = current_data
            market_state['last_update'] = time.time()
    finally:
        market_state['updating'] = False

# In main():
all_brackets = brackets + additional_brackets + reach_dip_brackets
threading.Thread(target=collect_market_data_async,
                 args=(all_brackets, event_id, market_state),
                 daemon=True).start()
```

---

## 3. Lock-Safe State Wrapper

Crucial for production stability. Initialize one lock in `main()` and use it for all writes.

```python
state_lock = threading.Lock()

# Inside any async thread:
def update_ai_analysis_async(current_data, previous_data, ai_state):
    try:
        # ... fetch response ...
        with state_lock:
            ai_state['analysis'] = response.output_text.strip()
            ai_state['last_update'] = time.time()
    finally:
        with state_lock:
            ai_state['updating'] = False
```

---

## 4. Curses Thread Safety

**NEVER** draw from a background thread. Curses state is global and will crash if accessed concurrently.

```python
# RIGHT: Draw in the main thread loop
while True:
    draw_ui(stdscr, ai_state, market_state) # Main thread only
    stdscr.refresh()
    key = stdscr.getch()

# WRONG: Do not do this
def thread_fn():
    stdscr.addstr(...) # CRASH
```

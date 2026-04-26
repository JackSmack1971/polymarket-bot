# Threading Lock Pattern (v3.0)

To prevent race conditions and ensure production stability, follow this pattern for all shared state dictionaries.

## 1. Define Global Locks
```python
import threading

# Initialize locks for each state dictionary
market_lock = threading.Lock()
ai_lock = threading.Lock()
btc_lock = threading.Lock()
```

## 2. Protected Async Function
The `updating = False` flag must be reset in a `finally` block, and all writes must be wrapped in the lock.

```python
def update_data_async(state, lock):
    """Background thread function."""
    try:
        # 1. Fetch data (outside lock to avoid blocking UI)
        new_data = fetch_external_api()
        
        # 2. Update state (inside lock)
        if new_data:
            with lock:
                state['data'] = new_data
                state['last_update'] = time.time()
                # Optional: state['history'].append(new_data)
                
    except Exception as e:
        with lock:
            state['error'] = str(e)
    finally:
        # 3. Reset updating flag (MANDATORY in finally)
        with lock:
            state['updating'] = False
```

## 3. Safe Main Loop Spawn
Gate the thread spawning in the main loop.

```python
# Inside main loop
if time.time() - state['last_update'] >= interval:
    # Use lock to check updating status
    with lock:
        should_start = not state['updating']
        if should_start:
            state['updating'] = True
    
    if should_start:
        thread = threading.Thread(
            target=update_data_async,
            args=(state, lock),
            daemon=True
        )
        thread.start()
```

## 4. UI Thread Read
Always use the lock when reading values that might be partially written by the background thread.

```python
with ai_lock:
    current_analysis = ai_state.get('analysis', 'Loading...')
    model_name = ai_state.get('model', 'AI')
```

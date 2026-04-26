# Polymarket BTC Terminal

## Run & Install

- Unified entry: `python main.py -e <event_id> -p <openai|openrouter>`
- OpenAI shim: `python poly_ui.py -e <event_id>`
- OpenRouter shim: `python poly_or.py -e <event_id>`
- Install: `pip install openai`

## Architecture: Modular R-C-S-R

The codebase has been refactored into a modular structure under `src/`:
- `src/repositories/`: API communication (Polymarket, CoinGecko) with exponential backoff.
- `src/services/`: Core business logic (AI analysis, price prediction math).
- `src/core/`: Centralized state management (thread-safe) and configuration.
- `src/ui/`: Curses rendering engine and layout management.

## Threading Model (Resolved)

All data sources use daemon threads managed via `src/core/state_manager.py`. 
- **Thread Safety**: Every state modification is wrapped in a `threading.Lock()` inside the respective state container.
- **Flag Management**: `updating` flags are strictly managed within `finally` blocks in background workers.

## Observability

- **Background Logging**: Thread exceptions and API warnings are logged to `bot.log`.
- **Render Discipline**: All Curses draw calls are strictly contained within the main thread's render loop.

## Output Contract

`extract_ai_price()` regex is `r'\$([0-9,]+)'`. The AI must return exactly: `Implied price: $XXX,XXX - [ONE insight ≤100 chars]`.

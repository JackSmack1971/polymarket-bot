# Polymarket BTC Terminal

## Run & Install

- OpenAI version: `python poly_ui.py -e <event_id>`
- OpenRouter version: `python poly_or.py -e <event_id>`
- Validate event: `python scripts/validate_event.py <event_id>`
- Validate AI output: `python scripts/validate_output_format.py "<response>"`
- Install: `pip install openai`

## Dependency Discipline

`openai` is the sole external dependency. Verify new capabilities against stdlib before introducing any package.

## Threading Model

All new data sources use `threading.Thread(..., daemon=True)` with a polling state dict: `{'data': None, 'last_update': 0, 'updating': False}`. Set `state['updating'] = False` as the final statement inside the async function — on attempt 1, before any return or exception. Gate thread spawning in the main loop via `stdscr.timeout(interval * 1000)` — the existing daemon pattern is the intended architecture.

## Render Discipline

All `curses` draw calls belong exclusively in the main thread render loop.

## AI Backend Difference

`poly_ui.py` uses `client.responses.create(reasoning={"effort":"high"})` + `.output_text`. `poly_or.py` uses `client.chat.completions.create()` (standard completions) + `.choices[0].message.content`. The `reasoning=` parameter is exclusive to the OpenAI client.

## Output Contract

`extract_ai_price()` regex is `r'\$([0-9,]+)'`. The AI must return exactly: `Implied price: $XXX,XXX - [ONE insight ≤100 chars]`. Format drift silently breaks the display pipeline.

## History Discipline

Slice `conversation_history` to `[-16:]` on every append cycle. `ai_price_history` and `btc_price_history` cap at 100 points with dedup filter `abs(new - last) > 0.01`.

## Known Bug

`ai_state['updating']  = False` is incorrectly set in the main loop after `thread.start()`. Move it to the final line of `update_ai_analysis_async()`.

## Priority Production Improvement

Wrap all state dict writes in `threading.Lock()` — no lock exists currently. Required before adding concurrent data sources.

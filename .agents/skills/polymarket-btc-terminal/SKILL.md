---
name: polymarket-btc-terminal
description: Expert development assistant for the Polymarket Bitcoin prediction terminal — a pure-curses, zero-dependency Python TUI with hacker Bloomberg aesthetics. Handles all development tasks across poly_ui.py (OpenAI Responses API) and poly_or.py (OpenRouter).
---

# Polymarket BTC Terminal — Development Skill

## Project Identity

Two parallel files, identical structure, different AI backends:
- `poly_ui.py` — OpenAI Responses API (`gpt-5-mini`, `reasoning={effort: "high"}`)
- `poly_or.py` — OpenRouter (`moonshotai/kimi-k2`)

**Aesthetic Symbols**: `▓▓▓` (Header), `▁▂▃▄▅▆▇█` (Sparkline), `●` (AI), `■` (Real).

---

## Curses Initialization

Crucial for the "Hacker Bloomberg" look:
- **Default Colors**: `curses.use_default_colors()` allows the terminal's background to show through.
- **Color Pairs**: 8 pairs configured, including `CYAN` (4) for borders and `MAGENTA` (8) for chart lines.
- **Transparency**: Uses `-1` for the background color in `init_pair`.

---

## Architecture & Layout

### Split-Pane Layout
- **Left**: Market data and AI analysis.
- **Right**: Bloomberg-style chart (`w > 95`).
- **Vertical Separator**: `│` character at `separator_col`.

### Render Loop
1. `stdscr.erase()`: Clear previous frame.
2. Calculate dimensions (`h, w`).
3. Trigger background threads (if interval elapsed).
4. Draw each section (`try/except curses.error` is mandatory).
5. `stdscr.refresh()`: Update the physical terminal.

---

## AI Backend Nuances

### OpenAI (poly_ui.py)
Uses the **Responses API**:
```python
client.responses.create(model="gpt-5-mini", reasoning={"effort":"high"}, input=messages)
```
- Output: `response.output_text`

### OpenRouter (poly_or.py)
Uses standard **Chat Completions**:
```python
client.chat.completions.create(model="moonshotai/kimi-k2", messages=messages)
```
- Output: `response.choices[0].message.content`

---

## Environment Setup (.env)
```bash
OPENAI_API_KEY=sk-proj-...
OPENROUTER_API_KEY=sk-or-v1-...
```

---

## Non-negotiables & Safety
1. **Never use `time.sleep()` in the main loop.** Use `stdscr.timeout()`.
2. **Horizontal Packing**: `draw_price_chart` uses `* 0.5` horizontal factor for high data density.
3. **Resizing**: Dimension calculation (`h, w = stdscr.getmaxyx()`) must occur at the start of every loop iteration to handle terminal resizing. `stdscr.erase()` prevents ghosting.
4. **Coordinate Bounds**: Always clamp `x` and `y` before `addstr`.
5. **Concurrency**: All shared state dicts (`ai_state`, `market_state`, `btc_state`) MUST be protected by a `threading.Lock()` for both reads and writes.
6. **Async Cleanup**: Background threads must reset their `updating` flag in a `finally` block to ensure system recovery after failures.

→ For chart math → `references/chart-engine.md`
→ For AI prompting → `references/ai-analysis.md`

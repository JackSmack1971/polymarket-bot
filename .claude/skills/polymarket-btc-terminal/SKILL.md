---
name: polymarket-btc-terminal
description: Expert development assistant for the Polymarket Bitcoin prediction terminal — a pure-curses, zero-dependency Python TUI with hacker Bloomberg aesthetics. Handles all development tasks across poly_ui.py (OpenAI Responses API) and poly_or.py (OpenRouter). Activates automatically whenever the user mentions: chart, curses, price history, sparkline, prediction, Polymarket, poly_ui, poly_or, draw_price_chart, AI vs real BTC, conversation history, market brackets, event ID, CoinGecko, CLOB, Gamma API, or any feature request for the terminal. Use this skill for bug fixes, new features, refactoring, layout changes, and architecture decisions. Do NOT use for unrelated Python projects or general charting work.
---

# Polymarket BTC Terminal — Development Skill

## Project Identity

Two parallel files, identical structure, different AI backends:
- `poly_ui.py` — OpenAI Responses API (`gpt-5-mini`, `reasoning={effort: "high"}`)
- `poly_or.py` — OpenRouter (`moonshotai/kimi-k2` or configurable)

**Non-negotiables**: pure `curses`, zero external deps except `openai`, hacker neon aesthetic. Never suggest `matplotlib`, `plotext`, or any external plotting library.

---

## Architecture Map

```
main(stdscr, event_id, interval, hist)
│
├── Background threads (daemon, shared-state dicts)
│   ├── update_btc_price_async(btc_state)          → CoinGecko
│   ├── collect_market_data_async(brackets, ...)   → Gamma + CLOB APIs
│   └── update_ai_analysis_async(data, prev, ai_state) → AI provider
│
├── Render loop (every `interval` seconds)
│   ├── Header row 0 — title + event + timestamp
│   ├── AI analysis rows 1-N (word-wrapped, italic yellow)
│   ├── Vertical separator │ at separator_col
│   ├── Market table (left side) — 3 event sections
│   │   ├── Event 37049 — Broad Ranges
│   │   ├── Event 36060 — Fine Ranges
│   │   └── Event 37057 — Reach/Dip
│   ├── draw_price_chart() (right side, only if w > 95)
│   └── Status bar row h-1 — Real BTC price + timestamp
│
└── Key handler: q/Q/ESC → exit
```

### Shared-State Dicts
```python
ai_state   = {'analysis': None, 'model': None, 'effort': None,
               'last_update': 0, 'updating': False,
               'conversation_history': []}  # max 16 msgs (8 pairs)

btc_state  = {'price': None, 'last_update': 0, 'updating': False}

market_state = {'current_data': None, 'last_update': 0, 'updating': False}
```

---

## Key Constants & Layout

| Constant | Value | Notes |
|---|---|---|
| `GAMMA_BASE` | `https://gamma-api.polymarket.com` | Event/market metadata |
| `CLOB_BASE` | `https://clob.polymarket.com` | Live yes/no prices |
| CoinGecko URL | `…/simple/price?ids=bitcoin&vs_currencies=usd` | Real BTC |
| Event 37049 | Broad ranges | `<120k`, `120-121k`, `>123k` |
| Event 36060 | Fine ranges | `$2k` brackets |
| Event 37057 | Reach/Dip | Volatility signals |
| Chart threshold | `w > 95` | Hides chart on narrow terminals |
| Chart width | `max(25, width - 5)` | Inside right panel |
| History cap | 100 points each | `ai_price_history`, `btc_price_history` |
| History append | `abs(new - last) > 0.01` | Dedup filter |
| Conversation cap | 16 messages | Last 8 user/assistant pairs |

### Color Pairs
```python
color_pair(1) = GREEN   # up arrows, real BTC ■, status bar
color_pair(2) = RED     # down arrows
color_pair(3) = YELLOW  # flat ▬, AI analysis text (italic), AI ●
color_pair(4) = CYAN    # headers, borders, chart title
color_pair(5) = GREEN BOLD   # sparkline up
color_pair(6) = RED BOLD     # sparkline down
color_pair(7) = neutral      # sparkline flat
```

---

## Common Development Tasks

### Adding a new feature to the chart
→ Read `references/chart-engine.md` first. All chart logic stays inside `draw_price_chart()`.

### Modifying AI behavior (system prompt, output format, model)
→ Read `references/ai-analysis.md` first.

### Adding a new Polymarket event or changing API logic
→ Read `references/data-layer.md` first.

### Layout changes (column widths, row counts, separator position)
- `separator_col` is calculated dynamically from terminal width
- AI analysis area width = `separator_col - 1`
- Chart area starts at `separator_col + 3`
- Always test at terminal widths 80, 100, 120, 140

### Sparkline rendering
- Lives inside the market table render loop, not in `draw_price_chart()`
- Uses `hist` parameter (default 30) for history length
- Per-bracket history stored in the `brackets` list items

### Threading safety
- All shared-state updates happen in background threads
- Main loop reads only — never write to state dicts from the render loop
- Set `state['updating'] = False` as the final line of every async function

---

## Strict Rules (Never Break)

1. `●` (yellow) = AI predictions. `■` (green) = Real BTC. Never swap, never rename.
2. The `* 0.5` horizontal spacing factor in `draw_price_chart()` is intentional — preserves 200% data density.
3. Never use `time.sleep()` in the render loop — use `curses.halfdelay()` or `stdscr.timeout()`.
4. All `stdscr.addstr()` calls must be wrapped in `try/except curses.error` to prevent terminal resize crashes.
5. `poly_ui.py` and `poly_or.py` changes must be kept in sync unless the user explicitly targets one file.
6. AI output format is locked: `"Implied price: $XXX,XXX - [ONE insight, max 100 chars]"`

---

## When Applying Fixes

1. Identify which file(s) are affected (`poly_ui.py`, `poly_or.py`, or both).
2. If touching chart logic → re-read `references/chart-engine.md`.
3. If touching AI prompt/memory → re-read `references/ai-analysis.md`.
4. Apply changes with `str_replace` (surgical, not full rewrites).
5. State the exact line numbers modified and why.

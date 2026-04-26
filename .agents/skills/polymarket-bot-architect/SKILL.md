---
name: polymarket-bot-architect
description: Guides development of the Polymarket curses TUI bot with daemon-threaded live data architecture. Use automatically when user mentions threading issues, async updates, market_state, ai_state, btc_state, background threads, UI freezing, high CPU, adding data sources, daemon threads, or any task involving poly_ui.py or poly_or.py.
---

# Polymarket Bot Architect — Working Knowledge (v3.0)

## Architecture Overview
Pure `curses` TUI with independent daemon threads for data ingestion. **V3.0 mandates modular R-C-S-R and Thread-Safe state management via `StateManager`.**

| Thread | Interval | State Object | Source | Lock Required |
|---|---|---|---|---|
| Market Data | 15s | `state.market` | Gamma + CLOB | `state.market.lock` |
| AI Analysis | 30s | `state.ai` | OpenAI/OpenRouter | `state.ai.lock` |
| BTC Price | 60s | `state.btc` | CoinGecko | `state.btc.lock` |

---

## 1. The Golden Threading Rules (CRITICAL)

### A. The StateManager & Dataclass Locks
Every shared state container is a dataclass protected by its own `threading.Lock()`.
- **Read/Write**: Always use `with state.[category].lock:` when updating or reading multiple attributes.
- **Access**: Use attribute access (`state.market.price_map`) instead of dictionary keys.

### B. The `updating = False` Pattern
Never set `updating = False` in the main loop or immediately after `thread.start()`.
- **Mandate**: It must be the **final statement** inside the `finally` block of the worker function itself.
- **Context**: Wrap it in a lock if the flag is part of the protected state.

---

## 2. Feature Risk Index (BFRI)
Before implementing new features or adding data sources, evaluate the risk:

| Score | Complexity | Risk | Impact | Action |
|---|---|---|---|---|
| **LOW** | Minor UI tweak | Low | Minimal | Proceed |
| **MED** | New API endpoint | Med | Potential Lag | Review Threading |
| **HIGH** | New Background Thread | High | Race Conditions | **Lock Audit Required** |

---

## 3. Modular R-C-S-R Structure
The codebase is strictly separated into `src/` layers:
- **Repositories**: `src/repositories/` (Polymarket, CoinGecko logic).
- **Services**: `src/services/` (AI analysis, price prediction math).
- **Core**: `src/core/` (StateManager, Orchestrator, Config).
- **UI**: `src/ui/` (Pure curses engine).

---

## 4. Output Contract Compliance
AI Analysis **MUST** adhere to the `GEMINI.md` contract:
- **Regex**: `r'\$([0-9,]+)'` is the gold standard for price extraction.
- **Format**: `Implied price: $XXX,XXX - [ONE insight ≤100 chars]`.
- **History**: Always slice `conversation_history` to `[-16:]`.

---

## UI & Aesthetics (Tribal Knowledge)
- **AI Analysis**: Prefix `[model-name]>` (BOLD GREEN), Text (ITALIC YELLOW).
- **Separator**: Vertical line `│` at `5/8` width.
- **Sparklines**: `▁▂▃▄▅▆▇█`. Use `* 0.5` factor for horizontal packing.

→ For lock templates → `references/threading-locks.md`
→ For API pattern contracts → `references/api-endpoints.md`
→ For threading templates → `references/thread-patterns.md`


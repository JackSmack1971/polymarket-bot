---
name: polymarket-bot-architect
description: Guides development of the Polymarket curses TUI bot with daemon-threaded live data architecture. Use automatically when user mentions threading issues, async updates, market_state, ai_state, btc_state, background threads, UI freezing, high CPU, adding data sources, daemon threads, or any task involving poly_ui.py or poly_or.py.
---

# Polymarket Bot Architect — Working Knowledge (v3.0)

## Architecture Overview
Pure `curses` TUI with independent daemon threads for data ingestion. **V3.0 mandates Thread-Safe state management.**

| Thread | Interval | State Dict | Source | Lock Required |
|---|---|---|---|---|
| Market Data | 25s | `market_state` | Gamma + CLOB | `market_lock` |
| AI Analysis | 30s | `ai_state` | OpenAI/OpenRouter | `ai_lock` |
| BTC Price | 60s | `btc_state` | CoinGecko | `btc_lock` |

---

## 1. The Golden Threading Rules (CRITICAL)

### A. The Global Threading Lock
Every shared state dictionary **MUST** be protected by a `threading.Lock()`.
- **Read/Write**: Always use `with state_lock:` when updating or reading multiple keys from a state dict.
- **Priority**: This is the top priority for production stability before adding concurrent data sources.

### B. The `updating = False` Pattern
Never set `updating = False` in the main loop or immediately after `thread.start()`.
- **Mandate**: It must be the **final statement** inside the `finally` block of the async function itself.
- **Reason**: Ensures the flag is reset even if an exception occurs, preventing deadlocks in data fetching.

---

## 2. Feature Risk Index (BFRI)
Before implementing new features or adding data sources, evaluate the risk:

| Score | Complexity | Risk | Impact | Action |
|---|---|---|---|---|
| **LOW** | Minor UI tweak | Low | Minimal | Proceed |
| **MED** | New API endpoint | Med | Potential Lag | Review Threading |
| **HIGH** | New Background Thread | High | Race Conditions | **Lock Audit Required** |

---

## 3. Architectural Evolution (Pythonic R-C-S-R)
Move away from monolithic files (`poly_ui.py`) towards a modular structure:
- **Repositories**: `api_client.py` (Gamma/CLOB/CoinGecko logic).
- **Services**: `prediction_logic.py` (Implied price calculations).
- **Controllers**: `state_manager.py` (Threading orchestration and Locks).
- **Render**: `ui_engine.py` (Pure curses draw calls).

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

# Polymarket AI Bitcoin Prediction Terminal

A hacker-style terminal application that synthesizes live Polymarket prediction market data into an AI-powered Bitcoin price estimate — updated in real time, rendered in a Bloomberg-style curses TUI.

> **v3.2.0** — Now with Structured Outputs, Hidden Chain-of-Thought, Live News RAG, Performance Ledger, and Multi-Model Consensus.

---

## Features

- **Structured AI Outputs** — Type-safe `implied_price`, `insight`, and hidden `internal_audit` fields via Pydantic, eliminating regex fragility
- **Hidden Chain-of-Thought** — AI performs an internal probability audit before emitting a price; reasoning stored in `bot.log`
- **Live News RAG** — Bitcoin headlines fetched every 5 min from RSS feeds and injected into the AI prompt for news-aware insights (e.g. *"Uptrend driven by ETF inflow news"*)
- **Performance Ledger** — Every AI prediction and live BTC price logged to `performance_ledger.jsonl` with error tracking
- **Multi-Model Consensus** — Optionally query OpenAI + OpenRouter simultaneously; a Judge Model resolves divergence above `$2,000`
- **Regime-Based α-Tuning** — Deterministic STABLE / MOMENTUM / REGIME CHANGE regimes with code-enforced move caps ($800 / $1,500)
- **Multi-Event Synthesis** — Probability-weighted EV across broad ranges (37049), fine ranges (36060), and reach/dip markets (37057)
- **Bloomberg-style TUI** — Sparkline charts, price comparison panel, live thread health footer
- **Multiple AI Providers** — OpenAI (`o3-mini`) or OpenRouter (`moonshotai/kimi-k2`), configurable in `config.py`
- **Thread-Safe Architecture** — Modular R-C-S-R with daemon threads and `threading.Lock`-protected state containers

---

## Prerequisites

- Python **3.8+**
- Terminal with color + italic support (256-color recommended)
- API keys for OpenAI and/or OpenRouter

---

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/JackSmack1971/polymarket-bot.git
cd polymarket-bot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

Dependencies: `openai`, `pydantic`, `requests`, `feedparser`, `windows-curses` (Windows only).

### 3. Configure API keys
Create a `.env` file in the project root:
```env
OPENAI_API_KEY=sk-proj-your-openai-key-here
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key-here
```

- **OpenAI key:** [platform.openai.com](https://platform.openai.com)
- **OpenRouter key:** [openrouter.ai](https://openrouter.ai) — access to 100+ models

---

## Usage

### Unified Entry Point (Recommended)
```bash
# OpenAI provider (o3-mini)
python main.py -e 37049 -p openai

# OpenRouter provider (moonshotai/kimi-k2)
python main.py -e 37049 -p openrouter
```

### Legacy Shims
```bash
python poly_ui.py -e 37049   # OpenAI
python poly_or.py -e 37049   # OpenRouter
```

### CLI Options
| Flag | Description | Default |
|---|---|---|
| `-e, --event` | Polymarket event ID to analyze (required) | — |
| `-p, --provider` | AI provider: `openai` or `openrouter` | `openai` |
| `-i, --interval` | UI refresh interval in seconds | `3` |
| `-H, --history` | Sparkline history length | `30` |

### Controls
- **`q` / `Q` / `ESC`** — Quit

---

## Display Layout

```
▓▓▓ POLYMARKET RANGE UI ▓▓▓  Event 37049  2026-04-26 15:30:00 UTC  [q: quit]

[o3-mini]> Implied price: $105,200 - ETF inflows sustaining upward momentum   │  ┌─ PRICE COMPARISON ──────────┐
                                                                                │  │ AI: ● Real: ■               │
Bracket                    Yes    No   Dir  Spark (Yes)                         │  │ $105,200                     │
────────────────────────────────────────────────────────────────────────────────┤  ├─────────────────────────────┤
Event 37049 (Broad Ranges):                                                     │  │   ●    ●    ●     ●         │
less than $110K...         0.120  0.870  ▼  ▁▁▂▁▁▂▁▁▁▂                        │  │                              │
between $110K and $112K... 0.430  0.560  ▲  ▂▃▄▄▅▆▆▇██                        │  │  ■    ■   ■    ■    ■       │
                                                                                │  │                              │
Event 36060 (Fine Ranges):                                                      │  │ $104,800                     │
between $104K and $106K... 0.380  0.610  ▲  ▃▄▄▅▆▆▇▇██                        │  └─────────────────────────────┘

Real BTC: $104,850.00 (updated 15:30:12)
[MKT 0.4s] [AI 28.1s] [BTC 55.2s] [NEWS 4m12s]
```

---

## How It Works

### Intelligence Pipeline

```
Polymarket API (15s) ──┐
CoinGecko API   (60s) ──┼──► StateManager ──► AIWorker (30s) ──► Structured Output
News RSS Feeds  (5m)  ──┘                          │
                                                   ▼
                              implied_price + insight + internal_audit
                                                   │
                                                   ▼
                              Performance Ledger (performance_ledger.jsonl)
```

1. **Market Data Collection** — `MarketWorker` fetches live prices for all 3 Polymarket event IDs every 15s
2. **EV Synthesis** — `PredictionService` computes a probability-weighted implied price (Main 35%, Fine 40%, Tail 25%) and PSI
3. **Regime Detection** — PSI determines STABLE / MOMENTUM / REGIME CHANGE; move caps enforced in code
4. **News RAG Injection** — Latest BTC headlines injected into the AI prompt for news-aware insights
5. **AI Analysis** — Structured output returns `internal_audit` (hidden CoT), `implied_price`, and `insight`
6. **Performance Logging** — Every prediction and actual BTC price logged to `performance_ledger.jsonl`

### α-Tuning Regimes

| Regime | PSI | α Weight | Move Cap |
|---|---|---|---|
| STABLE | < 0.02 | 0.70 (anchor to history) | $800 |
| MOMENTUM | 0.02 – 0.10 | 0.85 (follow fresh data) | $1,500 |
| REGIME CHANGE | > 0.10 | 1.00 (full market reset) | None |

---

## Configuration

Key settings in `src/core/config.py`:

```python
# AI Models
DEFAULT_OPENAI_MODEL = "o3-mini"
DEFAULT_OPENROUTER_MODEL = "moonshotai/kimi-k2"

# Multi-Model Consensus (disabled by default)
CONSENSUS_MODE = False                 # Set True to query both providers
CONSENSUS_DIVERGENCE_THRESHOLD = 2000  # $ spread triggering Judge arbitration
CONSENSUS_JUDGE_MODEL = "gpt-4o-mini"  # Fast, cheap arbitration model

# Polymarket Event IDs
EVENT_ID_MAIN        = 37049  # Broad ranges
EVENT_ID_FINE_RANGES = 36060  # Fine ranges
EVENT_ID_REACH_DIP   = 37057  # Reach/dip tail markets
```

---

## Performance Ledger

The bot automatically maintains `performance_ledger.jsonl` in the project root. Each line is a JSON record:

```jsonl
{"type": "prediction", "timestamp": 1745679000.0, "iso": "2026-04-26T15:30:00Z", "implied_price": 105200}
{"type": "actual", "timestamp": 1745679060.0, "iso": "2026-04-26T15:31:00Z", "actual_price": 104850.0, "last_implied": 105200, "prediction_error": 350.0}
```

Prediction errors are also logged to `bot.log` in real time:
```
EvaluationService: Error=+$350 (0.33%) | Implied=$105,200 vs Actual=$104,850
```

---

## Architecture

The codebase follows a strict **R-C-S-R** layered architecture under `src/`:

```
src/
├── core/
│   ├── config.py          # Centralized configuration & event IDs
│   ├── state_manager.py   # Thread-safe state containers (Market, AI, BTC, News)
│   └── orchestrator.py    # Thread lifecycle & worker scheduling
├── repositories/
│   ├── base_api.py        # Exponential backoff HTTP client
│   ├── polymarket.py      # Gamma + CLOB API access
│   ├── coingecko.py       # Live BTC price fetching
│   └── news.py            # RSS news feed aggregator
├── services/
│   ├── prediction_service.py  # EV synthesis, PSI, arbitrage detection
│   ├── ai_service.py          # Structured AI output, α-Tuning, move caps
│   ├── consensus_service.py   # Multi-model ensemble + Judge arbitration
│   └── evaluation_service.py  # Performance ledger (JSONL append-only log)
└── ui/
    ├── renderer.py        # Pure curses rendering engine
    └── histogram.py       # Sparkline chart components
```

### Background Thread Schedule

| Worker | Interval | Data Source | State Object |
|---|---|---|---|
| `MarketWorker` | 15s | Polymarket Gamma + CLOB | `state.market` |
| `AIWorker` | 30s | OpenAI / OpenRouter | `state.ai` |
| `BTCWorker` | 60s | CoinGecko | `state.btc` |
| `NewsWorker` | 5 min | RSS Feeds | `state.news` |

---

## Troubleshooting

**`AI unavailable` message:**
- Check `OPENAI_API_KEY` or `OPENROUTER_API_KEY` in `.env`
- Verify the key has sufficient credits

**Chart not displaying:**
- Ensure terminal width > 95 characters and height > 40 lines
- Use a monospace font (Courier New, JetBrains Mono, Monaco)

**Import errors (`pydantic`, `feedparser`):**
- Run `pip install -r requirements.txt`
- Ensure Python 3.8+ is active

**News headlines not appearing:**
- `NewsWorker` fires 5 min after startup; check `bot.log` for feed errors
- Fallback: AI runs normally without news context if all feeds fail

**Consensus mode issues:**
- Ensure **both** `OPENAI_API_KEY` and `OPENROUTER_API_KEY` are set when `CONSENSUS_MODE = True`
- Check `bot.log` for Judge model errors

---

## Terminal Setup for Best Experience

1. Set font to **JetBrains Mono**, **Courier New**, or **Monaco**
2. Enable **italic text support** in terminal emulator settings
3. Use a **dark background** with high contrast
4. Maximize window — minimum recommended: **140×45** characters

---

## Contributing

Pull requests welcome. Please follow the R-C-S-R layered architecture — routes/controllers/services/repositories — and ensure new background threads use `threading.Lock` for all state mutations.

---

## License

MIT License — Feel free to modify and distribute.

---

## Disclaimer

This tool is for educational and research purposes only. Cryptocurrency predictions are inherently uncertain and should not be used as the sole basis for trading decisions. Past performance does not guarantee future results.

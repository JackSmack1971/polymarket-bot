# Polymarket AI Bitcoin Prediction Terminal

A hacker-style terminal application that analyzes Bitcoin prediction markets on Polymarket and provides AI-powered price predictions with real-time chart visualization.

## Features

- **Real-time market analysis** from multiple Polymarket events
- **AI-powered Bitcoin price predictions** with conversation memory
- **Bloomberg-style price charts** comparing AI predictions vs real BTC prices
- **Hacker terminal aesthetic** with neon colors and courier fonts
- **Multiple AI providers** - OpenAI Reasoning API or OpenRouter
- **Live sparkline charts** showing market probability trends
- **Multi-event analysis** (broad ranges, fine ranges, reach/dip markets)

## Prerequisites

- Python 3.7+
- Terminal with color support
- API keys (see Setup section)

## Setup

1. **Clone the repository:**
```bash
git clone https://github.com/All-About-AI-YouTube/polymarket_ai_bitcoin.git
cd polymarket_ai_bitcoin
```

2. **Install dependencies:**
```bash
pip install openai
```

3. **Create `.env` file with your API keys:**
```bash
# For OpenAI version (poly_ui.py)
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# For OpenRouter version (poly_or.py) 
OPENROUTER_API_KEY=sk-or-v1-your-openrouter-key-here
```

4. **Get API keys:**
   - **OpenAI:** Get from [platform.openai.com](https://platform.openai.com)
   - **OpenRouter:** Get from [openrouter.ai](https://openrouter.ai) (access to 100+ models)

## Usage

### OpenAI Version (with Reasoning API)
```bash
python poly_ui.py -e 37049
```

### OpenRouter Version (with Claude, Llama, etc.)
```bash
python poly_or.py -e 37049
```

### Command Line Options
- `-e, --event` - Event ID to analyze (required, e.g., 37049)
- `-i, --interval` - Refresh interval in seconds (default: 3)
- `-H, --history` - Sparkline history length (default: 30)

### Controls
- **q/Q/ESC** - Quit the application
- Terminal will auto-refresh every few seconds

## Display Layout

```
▓▓▓ POLYMARKET RANGE UI ▓▓▓  Event 37049  2025-08-12 08:07:08 UTC  [q: quit]

[gpt-5-mini-high]> Implied price: $119,078 - Strong 116-120k cluster     │  ┌─ PRICE COMPARISON ────────┐
    bearish dip signals                                                  │  │ AI: ● Real: ■              │
                                                                         │  │ $119,716                    │
Bracket                    Yes    No   Dir  Spark (Yes)                  │  ├────────────────────────────┤
────────────────────────────────────────────────────────────────────────┤  │                            │
Event 37049 (Broad Ranges):                                             │  │    ●    ●    ●      ●     │
less than $120K Aug 12...  0.750  0.230  ▬  ████████████████████████    │  │                            │
between $120K and $121K... 0.140  0.840  ▬  ████████████████████████    │  │  ■    ■    ■    ■    ■   │
                                                                         │  │                            │
Event 36060 (Fine Ranges):                                              │  │                            │
between $114K and...       0.050  0.926  ▲  ████████████████████████    │  │         ●                 │
between $116K and...       0.220  0.770  ▬  ████████████████████████    │  │                            │
                                                                         │  │                            │
Event 37057 (Reach/Dip):                                                │  │                            │
dip $118k Aug 11-1...      0.800  0.150  ▬  ████████████████████████    │  │ $118,622                   │
                                                                         │  └────────────────────────────┘

Real BTC: $118,938.00 (updated 10:06:26)
```

## How It Works

1. **Market Data Collection:** Fetches live prediction market data from multiple Polymarket events
2. **AI Analysis:** Uses conversation memory to provide consistent Bitcoin price predictions
3. **Probability Analysis:** Calculates probability-weighted price estimates across market brackets  
4. **Visualization:** Real-time charts comparing AI predictions vs actual BTC prices
5. **Multi-Event Synthesis:** Combines broad ranges, fine ranges, and reach/dip data for accuracy

## Event IDs

Common Bitcoin prediction market events:
- `37049` - Broad price ranges (e.g., <$120k, $120-121k, >$123k)
- `36060` - Fine price ranges (e.g., $114-116k, $116-118k)
- `37057` - Reach/dip events (e.g., "Will BTC reach $125k?")

## Terminal Setup for Best Experience

For the full hacker aesthetic:
1. Set terminal font to **Courier New** or **Monaco**
2. Enable **italic text support**  
3. Use **dark background** with high contrast
4. Maximize terminal window for chart visibility

## Models

- **OpenAI version:** Uses `gpt-5-mini` with reasoning API for enhanced analysis
- **OpenRouter version:** Uses `moonshotai/kimi-k2` or other models (configurable in code)

## Troubleshooting

**"AI unavailable" message:**
- Check your API key in `.env` file
- Verify API key has sufficient credits
- Check internet connection

**Chart not displaying:**
- Ensure terminal width > 95 characters
- Increase terminal height for full display

**Import errors:**
- Install openai: `pip install openai`
- Ensure Python 3.7+ is installed

## Contributing

Pull requests welcome! This is a terminal-based AI prediction tool built for the crypto community.

## License

MIT License - Feel free to modify and distribute.

## Disclaimer

This tool is for educational and research purposes only. Cryptocurrency predictions are inherently uncertain and should not be used as sole basis for trading decisions. Past performance does not guarantee future results.

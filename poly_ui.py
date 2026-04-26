#!/usr/bin/env python3
import argparse, curses, json, time, os, threading
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from openai import OpenAI

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE  = "https://clob.polymarket.com"

# Load OpenAI API key from .env
try:
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('OPENAI_API_KEY='):
                os.environ['OPENAI_API_KEY'] = line.split('=', 1)[1].strip()
except FileNotFoundError:
    pass

client = OpenAI()

def http_get_json(url, timeout=10):
    req = Request(url, headers={"User-Agent": "poly-ui/1.0"})
    with urlopen(req, timeout=timeout) as r:
        data = r.read()
    try:
        return json.loads(data.decode("utf-8"))
    except json.JSONDecodeError:
        # Sometimes /price returns a raw number, not JSON. Make it JSON.
        s = data.decode("utf-8").strip()
        try:
            return float(s)
        except Exception:
            return None

def fetch_event_markets(event_id):
    """Return list of brackets with yes/no token IDs."""
    url = f"{GAMMA_BASE}/events/{event_id}"
    ev = http_get_json(url)
    if not ev or "markets" not in ev:
        raise RuntimeError("No markets found for event")
    rows = []
    for m in ev["markets"]:
        try:
            tokens = json.loads(m.get("clobTokenIds","[]"))
            prices = json.loads(m.get("outcomePrices","[]"))
            outcomes = json.loads(m.get("outcomes","[]"))
        except Exception:
            continue
        if len(tokens)!=2 or len(prices)!=2 or outcomes!=["Yes","No"]:
            continue
        q = m.get("question","")
        rows.append({
            "bracket": q,
            "yes_token": tokens[0],
            "no_token":  tokens[1],
        })
    # Keep a logical order: <120k, 120-121k, ..., >123k
    def keyer(q):
        s = q["bracket"].lower()
        # push "<…", then ranges, then ">…"
        if s.startswith("will the price of bitcoin be less"):
            return (0, s)
        if "between" in s:
            return (1, s)
        if "greater" in s:
            return (2, s)
        return (9, s)
    rows.sort(key=keyer)
    return rows

def fetch_price(token_id, side="buy"):
    """Return executable BUY price (float). Handles both raw number and {price:...}."""
    url = f"{CLOB_BASE}/price?token_id={token_id}&side={side}"
    j = http_get_json(url)
    if j is None:
        return None
    if isinstance(j, dict):
        return float(j.get("price")) if j.get("price") is not None else None
    if isinstance(j, (int, float)):
        return float(j)
    return None

SPARK_LEVELS = "▁▂▃▄▅▆▇█"

def spark_segments(values, width=12):
    """
    Return a list of (char, delta) for the last `width` samples.
    delta: -1 (down), 0 (flat), +1 (up) vs previous sample.
    """
    if not values:
        return []

    vals = values[-width:]
    lo, hi = min(vals), max(vals)
    segs = []
    for i, v in enumerate(vals):
        # normalize to 0..1 for height char
        t = 0 if hi == lo else (v - lo) / (hi - lo)
        idx = min(len(SPARK_LEVELS)-1, max(0, int(t*(len(SPARK_LEVELS)-1))))
        ch = SPARK_LEVELS[idx]

        # direction vs previous sample
        if i == 0:
            delta = 0
        else:
            prev = vals[i-1]
            eps = 1e-6
            if v > prev + eps:
                delta = +1
            elif v < prev - eps:
                delta = -1
            else:
                delta = 0
        segs.append((ch, delta))
    return segs

def draw_colored_spark(stdscr, row, col, values, width, color_up, color_down, color_flat):
    segs = spark_segments(values, width)
    c = col
    for ch, delta in segs:
        if   delta > 0: color = color_up
        elif delta < 0: color = color_down
        else:           color = color_flat
        stdscr.addstr(row, c, ch, color)
        c += 1

def trim_bracket_label(text, maxw):
    # Make "Will the price of Bitcoin be … at 5PM ET?" → "… <120k", "120–121k", etc.
    t = text
    t = t.replace("Will the price of Bitcoin be ", "")
    t = t.replace(" on ", " ")
    t = t.replace(" at ", " ")
    t = t.replace("August", "Aug")
    t = t.replace("  ", " ")
    if len(t) > maxw:
        t = t[:maxw-1] + "…"
    return t

def wrap_ai_text(text, width, model="AI", effort=""):
    """Wrap AI text to fit screen width, returning list of lines."""
    if not text:
        return [""]
    
    # Create hacker-style prefix with model and effort info
    effort_suffix = f"-{effort}" if effort else ""
    prefix = f"[{model}{effort_suffix}]> "
    
    # Remove old "AI: " prefix if present for wrapping calculation
    clean_text = text.replace("AI: ", "").strip()
    
    words = clean_text.split()
    lines = []
    current_line = prefix
    
    for word in words:
        # Check if adding this word would exceed width
        if len(current_line + word) + 1 <= width:
            if current_line == prefix:
                current_line += word
            else:
                current_line += " " + word
        else:
            # Start new line
            lines.append(current_line)
            current_line = "    " + word  # Indent continuation lines
    
    if current_line.strip():
        lines.append(current_line)
    
    return lines if lines else [prefix]

def fetch_additional_event_data(event_id):
    """Fetch data from additional event for more granular analysis."""
    try:
        url = f"{GAMMA_BASE}/events/{event_id}"
        ev = http_get_json(url)
        if not ev or "markets" not in ev:
            return []
        
        rows = []
        for m in ev["markets"]:
            try:
                tokens = json.loads(m.get("clobTokenIds","[]"))
                prices = json.loads(m.get("outcomePrices","[]"))
                outcomes = json.loads(m.get("outcomes","[]"))
            except Exception:
                continue
            if len(tokens)!=2 or len(prices)!=2 or outcomes!=["Yes","No"]:
                continue
            q = m.get("question","")
            rows.append({
                "bracket": q,
                "yes_token": tokens[0],
                "no_token":  tokens[1],
                "yes_price": float(prices[0]),
                "no_price": float(prices[1])
            })
        return rows
    except Exception:
        return []

def calculate_implied_bitcoin_price(brackets, additional_event_id=36060):
    """Calculate implied Bitcoin price from market probabilities with additional data."""
    try:
        # Get additional fine-grained data
        additional_data = fetch_additional_event_data(additional_event_id)
        
        # Extract price ranges and probabilities from main event
        ranges = []
        for b in brackets:
            if b.get("last_yes") is None:
                continue
                
            bracket = b["bracket"].lower()
            yes_prob = b["last_yes"]
            
            # Parse price ranges from bracket descriptions
            if "less than" in bracket and "120" in bracket:
                ranges.append({"range": "< 120k", "prob": yes_prob, "mid": 115000, "source": "main"})
            elif "between" in bracket and "120" in bracket and "121" in bracket:
                ranges.append({"range": "120-121k", "prob": yes_prob, "mid": 120500, "source": "main"})
            elif "between" in bracket and "121" in bracket and "122" in bracket:
                ranges.append({"range": "121-122k", "prob": yes_prob, "mid": 121500, "source": "main"})
            elif "between" in bracket and "122" in bracket and "123" in bracket:
                ranges.append({"range": "122-123k", "prob": yes_prob, "mid": 122500, "source": "main"})
            elif "greater than" in bracket and "123" in bracket:
                ranges.append({"range": "> 123k", "prob": yes_prob, "mid": 125000, "source": "main"})
        
        # Add fine-grained ranges from additional event
        for a in additional_data:
            bracket = a["bracket"].lower()
            yes_prob = a["yes_price"]
            
            if "less than" in bracket and "110" in bracket:
                ranges.append({"range": "< 110k", "prob": yes_prob, "mid": 105000, "source": "fine_ranges"})
            elif "between" in bracket and "110" in bracket and "112" in bracket:
                ranges.append({"range": "110-112k", "prob": yes_prob, "mid": 111000, "source": "fine_ranges"})
            elif "between" in bracket and "112" in bracket and "114" in bracket:
                ranges.append({"range": "112-114k", "prob": yes_prob, "mid": 113000, "source": "fine_ranges"})
            elif "between" in bracket and "114" in bracket and "116" in bracket:
                ranges.append({"range": "114-116k", "prob": yes_prob, "mid": 115000, "source": "fine_ranges"})
            elif "between" in bracket and "116" in bracket and "118" in bracket:
                ranges.append({"range": "116-118k", "prob": yes_prob, "mid": 117000, "source": "fine_ranges"})
            elif "greater than" in bracket and "118" in bracket:
                ranges.append({"range": "> 118k", "prob": yes_prob, "mid": 120000, "source": "fine_ranges"})
        
        # Add reach/dip data from third event (different perspective)
        reach_dip_data = fetch_additional_event_data(37057)
        for r in reach_dip_data:
            bracket = r["bracket"].lower()
            yes_prob = r["yes_price"]
            
            if "reach" in bracket and "$127k" in bracket:
                ranges.append({"range": "reach_127k", "prob": yes_prob, "mid": 127000, "source": "reach_dip"})
            elif "reach" in bracket and "$125k" in bracket:
                ranges.append({"range": "reach_125k", "prob": yes_prob, "mid": 125000, "source": "reach_dip"})
            elif "reach" in bracket and "$123k" in bracket:
                ranges.append({"range": "reach_123k", "prob": yes_prob, "mid": 123000, "source": "reach_dip"})
            elif "dip to" in bracket and "$120k" in bracket:
                # Skip - this market resolved when BTC hit $120k
                continue
            elif "dip to" in bracket and "$118k" in bracket:
                ranges.append({"range": "dip_118k", "prob": yes_prob, "mid": 118000, "source": "reach_dip"})
            elif "dip to" in bracket and "$116k" in bracket:
                ranges.append({"range": "dip_116k", "prob": yes_prob, "mid": 116000, "source": "reach_dip"})
        
        if not ranges:
            return None
            
        # Calculate probability-weighted average price
        total_weighted = sum(r["prob"] * r["mid"] for r in ranges)
        total_prob = sum(r["prob"] for r in ranges)
        
        if total_prob > 0:
            implied_price = total_weighted / total_prob
            
            # Find most likely range
            max_prob_range = max(ranges, key=lambda x: x["prob"])
            
            return {
                "implied_price": round(implied_price),
                "most_likely_range": max_prob_range["range"],
                "max_probability": round(max_prob_range["prob"], 3),
                "ranges": ranges,
                "data_sources": len([r for r in ranges if r["source"] == "additional"])
            }
    except Exception:
        pass
    
    return None

def format_market_data_for_ai(brackets, event_id):
    """Format current market data for AI analysis."""
    data = {
        "event_id": event_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "markets": []
    }
    
    for b in brackets:
        if b.get("last_yes") is not None and b.get("last_no") is not None:
            # Calculate direction based on recent history
            yes_trend = "flat"
            if len(b["yes_hist"]) >= 2:
                recent_change = b["yes_hist"][-1] - b["yes_hist"][-2]
                if recent_change > 1e-4:
                    yes_trend = "up"
                elif recent_change < -1e-4:
                    yes_trend = "down"
            
            market_info = {
                "bracket": b["bracket"],
                "yes_price": b["last_yes"],
                "no_price": b["last_no"],
                "yes_trend": yes_trend,
                "price_history_samples": len(b["yes_hist"])
            }
            data["markets"].append(market_info)
    
    # Add Bitcoin price prediction
    price_prediction = calculate_implied_bitcoin_price(brackets)
    if price_prediction:
        data["bitcoin_prediction"] = price_prediction
    
    return data

def fetch_btc_price():
    """Fetch current BTC price from CoinGecko API."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        j = http_get_json(url, timeout=5)
        if j and "bitcoin" in j and "usd" in j["bitcoin"]:
            return j["bitcoin"]["usd"]
    except Exception:
        pass
    return None

def update_btc_price_async(btc_state):
    """Update real BTC price in background thread."""
    try:
        price = fetch_btc_price()
        if price:
            btc_state['price'] = price
            btc_state['last_update'] = time.time()
    except Exception:
        pass
    btc_state['updating'] = False

def collect_market_data_async(brackets, event_id, market_state):
    """Collect market data for AI analysis in background thread."""
    try:
        current_data = format_market_data_for_ai(brackets, event_id)
        if current_data["markets"]:
            market_state['current_data'] = current_data
            market_state['last_update'] = time.time()
    except Exception:
        pass
    market_state['updating'] = False

def update_ai_analysis_async(current_data, previous_data, ai_state):
    """Update AI analysis in background thread with conversation history."""
    try:
        # Build conversation messages with history
        messages = [
            {
                "role": "system",
                "content": """You are a quantitative Bitcoin price prediction specialist analyzing Polymarket prediction markets with mathematical precision.

Core analytical framework:
1. PROBABILITY DENSITY FUNCTION: Calculate the implied probability distribution across all price ranges
2. EXPECTED VALUE: Compute probability-weighted mean price = Σ(price_midpoint × probability)
3. CONFIDENCE INTERVALS: Identify 68% and 95% confidence ranges based on cumulative probability
4. MARKET EFFICIENCY: Detect arbitrage when sum of related probabilities ≠ 1.0
5. MOMENTUM INDICATORS: Track probability flow between adjacent brackets (increasing/decreasing)
6. VOLATILITY METRICS: Reach/dip markets indicate expected volatility, not just ending price

Data hierarchy for analysis:
- FINE RANGES (Event 36060): Most granular, $2k brackets, highest weight (40%)
- BROAD RANGES (Event 37049): Wider brackets, medium weight (35%) 
- REACH/DIP (Event 37057): Volatility indicators, lower weight (25%)

Key calculations to perform:
1. Find the bracket with maximum probability (mode)
2. Calculate weighted average across all brackets (mean)
3. Identify probability mass concentration (>70% in 2-3 adjacent brackets = strong signal)
4. Compare reach vs dip probabilities (reach > dip = bullish momentum)
5. Track your prediction accuracy: compare previous estimates to actual movements

PRICE CONSISTENCY RULES:
- Large price jumps (>$2000) between predictions require strong justification
- If market probabilities haven't shifted dramatically, price should move <$1000
- Weight your previous prediction at 30% unless major market shift occurred
- New prediction = 70% * fresh_calculation + 30% * previous_prediction (if <2% probability change)
- Only make big jumps when probability distributions show clear regime change

Critical rules:
- If probabilities sum > 1.05 or < 0.95 across brackets, flag data quality issue
- Weight recent probability changes more heavily (last 2 updates = 60% weight)
- When fine/broad ranges disagree by >$2k, trust fine ranges more
- Adjust predictions based on your historical accuracy trend

OUTPUT REQUIREMENTS - CRITICAL:
- Maximum 100 characters after price
- Focus on ONE key insight only
- No technical jargon or calculations in output
- Be extremely concise and direct

Format: "Implied price: $XXX,XXX - [ONE key insight, max 100 chars]"
Good: "Implied price: $119,250 - 68% mass in 118-120k, mild upward momentum"
Bad: "Implied price: $119,250 - Maximum probability concentration across fine-grained brackets indicates 68% probability mass concentrated in the 118-120k range with reach_125k at 0.32 suggesting upward pressure despite dip signals" """
            }
        ]
        
        # Add conversation history (last 8 interactions)
        for hist in ai_state['conversation_history'][-16:]:  # Keep last 16 messages (8 pairs)
            messages.append(hist)
        
        # Add current market data prompt
        if len(ai_state['conversation_history']) == 0:
            prompt = f"""Analyze these Bitcoin prediction markets and provide:
1. Your own implied Bitcoin price estimate 
2. Brief reasoning based on the probability distributions

Current market data:
{json.dumps(current_data, indent=2)}

Format: "Implied price: $X - [brief analysis of what the markets suggest]" """
        else:
            prompt = f"""Here's updated Bitcoin prediction market data. Consider your previous analyses and predictions:

CURRENT MARKET DATA:
{json.dumps(current_data, indent=2)}

Provide updated analysis:
1. Your new implied Bitcoin price estimate
2. Brief explanation of any changes in market sentiment
3. Reflection on how your previous predictions are performing

Format: "Implied price: $X - [brief analysis of changes and prediction accuracy]" """
        
        messages.append({
            "role": "user",
            "content": prompt
        })

        model = "gpt-5-mini"
        effort = "high"
        response = client.responses.create(
            model=model,
            reasoning={"effort": effort},
            input=messages
        )
        
        # Store the interaction in conversation history
        ai_state['conversation_history'].append({
            "role": "user",
            "content": prompt
        })
        ai_state['conversation_history'].append({
            "role": "assistant", 
            "content": response.output_text.strip()
        })
        
        # Keep only last 8 interactions (16 messages)
        ai_state['conversation_history'] = ai_state['conversation_history'][-16:]
        
        ai_state['analysis'] = response.output_text.strip()
        ai_state['model'] = model
        ai_state['effort'] = effort
        ai_state['last_update'] = time.time()
    except Exception as e:
        ai_state['analysis'] = f"AI unavailable: {str(e)[:30]}..."

def extract_ai_price(ai_text):
    """Extract implied price from AI analysis text."""
    import re
    # Look for patterns like "Implied price: $118,689" or "$118,689"
    match = re.search(r'\$([0-9,]+)', ai_text)
    if match:
        try:
            return float(match.group(1).replace(',', ''))
        except:
            pass
    return None


def draw_price_chart(stdscr, start_row, start_col, width, height, ai_prices, btc_prices):
    """Draw a Bloomberg-style price comparison chart with line graphs."""
    if len(ai_prices) < 1 and len(btc_prices) < 1:
        stdscr.addstr(start_row, start_col, "Price Chart", curses.color_pair(4) | curses.A_BOLD)
        stdscr.addstr(start_row + 1, start_col, "Collecting data...")
        return
    
    # Chart dimensions - use most of available space
    chart_width = max(25, width - 5)  # Use almost all available width
    chart_height = max(10, height - 3)  # Use almost all available height
    
    # Get recent data points - pack more data by reducing spacing
    max_points = max(60, (chart_width - 10) * 2)  # Double the data points for tighter spacing
    ai_data = ai_prices[-max_points:] if ai_prices else []
    btc_data = btc_prices[-max_points:] if btc_prices else []
    
    # Pad shorter series with None to align them
    max_len = max(len(ai_data), len(btc_data))
    if len(ai_data) < max_len:
        ai_data = [None] * (max_len - len(ai_data)) + ai_data
    if len(btc_data) < max_len:
        btc_data = [None] * (max_len - len(btc_data)) + btc_data
        
    # Find price range for scaling
    all_prices = [p for p in ai_data + btc_data if p is not None]
    if not all_prices:
        return
        
    min_price, max_price = min(all_prices), max(all_prices)
    if min_price == max_price:
        min_price -= 100
        max_price += 100
        
    # Chart header and legend - use full available width
    inner_width = chart_width - 2
    title = "─ PRICE COMPARISON "
    remaining = max(0, inner_width - len(title))
    border_line = "─" * remaining
    
    stdscr.addstr(start_row, start_col, f"┌{title}{border_line}┐", curses.color_pair(4) | curses.A_BOLD)
    stdscr.addstr(start_row + 1, start_col, f"│ AI: ● Real: ■{' ' * max(0, inner_width - 14)} │")
    stdscr.addstr(start_row + 2, start_col, f"│ ${max_price:,.0f}".ljust(inner_width) + " │")
    stdscr.addstr(start_row + 3, start_col, "│" + "─" * inner_width + "│")
    
    # Draw chart grid
    for row in range(chart_height):
        y_pos = start_row + 4 + row
        if y_pos < stdscr.getmaxyx()[0] - 2:
            if row == chart_height - 1:
                stdscr.addstr(y_pos, start_col, "│" + "─" * (chart_width - 2) + "│")
                stdscr.addstr(y_pos + 1, start_col, f"│ ${min_price:,.0f}".ljust(chart_width - 1) + "│")
                stdscr.addstr(y_pos + 2, start_col, "└" + "─" * (chart_width - 2) + "┘")
            else:
                stdscr.addstr(y_pos, start_col, "│" + " " * (chart_width - 2) + "│")
    
    # Plot data with line connections
    chart_start_x = start_col + 2
    chart_start_y = start_row + 4
    
    # Plot AI data points (yellow)
    prev_ai_y = None
    prev_ai_x = None
    plot_width = chart_width - 4  # Available plotting width inside borders
    
    for i, price in enumerate(ai_data):
        if price is not None:
            # Closer horizontal spacing (200% closer as requested)
            x = chart_start_x + int(i * (plot_width / max(2, max_len - 1)) * 0.5) if max_len > 1 else chart_start_x
            y_ratio = (price - min_price) / (max_price - min_price) if max_price > min_price else 0.5
            y = chart_start_y + int((1 - y_ratio) * (chart_height - 2))
            
            # Ensure coordinates are within bounds
            x = max(chart_start_x, min(x, start_col + chart_width - 3))
            y = max(chart_start_y, min(y, chart_start_y + chart_height - 2))
            
            try:
                # Draw the data point only
                stdscr.addstr(y, x, "●", curses.color_pair(3) | curses.A_BOLD)  # Bright yellow dot
                prev_ai_y = y
                prev_ai_x = x
            except curses.error:
                pass
    
    # Plot BTC data points (green)
    prev_btc_y = None
    prev_btc_x = None
    for i, price in enumerate(btc_data):
        if price is not None:
            # Same closer horizontal spacing as AI data
            x = chart_start_x + int(i * (plot_width / max(2, max_len - 1)) * 0.5) if max_len > 1 else chart_start_x
            y_ratio = (price - min_price) / (max_price - min_price) if max_price > min_price else 0.5
            y = chart_start_y + int((1 - y_ratio) * (chart_height - 2))
            
            # Ensure coordinates are within bounds
            x = max(chart_start_x, min(x, start_col + chart_width - 3))
            y = max(chart_start_y, min(y, chart_start_y + chart_height - 2))
            
            try:
                # Draw the data point only (offset right to avoid AI overlap)
                if x + 1 < start_col + chart_width - 2:
                    stdscr.addstr(y, x + 1, "■", curses.color_pair(1))  # Green square
                prev_btc_y = y
                prev_btc_x = x
            except curses.error:
                pass

def main(stdscr, event_id, interval, hist):
    curses.curs_set(0)
    curses.use_default_colors()
    # Colors
    curses.init_pair(1, curses.COLOR_GREEN, -1)  # up
    curses.init_pair(2, curses.COLOR_RED, -1)    # down
    curses.init_pair(3, curses.COLOR_YELLOW, -1) # flat
    curses.init_pair(4, curses.COLOR_CYAN, -1)   # headings
    curses.init_pair(5, curses.COLOR_GREEN, -1)  # spark up
    curses.init_pair(6, curses.COLOR_RED,   -1)  # spark down
    curses.init_pair(7, -1,                 -1)  # spark flat (default fg)
    curses.init_pair(8, curses.COLOR_MAGENTA, -1)  # purple connecting lines
    
    # Load brackets from main event
    try:
        brackets = fetch_event_markets(event_id)
    except Exception as e:
        stdscr.addstr(0,0,f"Error: {e}\n")
        stdscr.refresh()
        time.sleep(3)
        return
    if not brackets:
        stdscr.addstr(0,0,"No suitable markets (Yes/No) found in this event.")
        stdscr.refresh(); time.sleep(3); return

    # Load brackets from additional events
    try:
        additional_brackets = fetch_event_markets(36060)
    except Exception:
        additional_brackets = []
        
    try:
        reach_dip_brackets = fetch_event_markets(37057)
    except Exception:
        reach_dip_brackets = []

    # State for main event
    for b in brackets:
        b["yes_hist"] = []
        b["no_hist"] = []
        b["last_yes"] = None
        b["last_no"]  = None
        b["event_id"] = event_id

    # State for additional event
    for b in additional_brackets:
        b["yes_hist"] = []
        b["no_hist"] = []
        b["last_yes"] = None
        b["last_no"]  = None
        b["event_id"] = 36060
        
    # State for reach/dip event
    for b in reach_dip_brackets:
        b["yes_hist"] = []
        b["no_hist"] = []
        b["last_yes"] = None
        b["last_no"]  = None
        b["event_id"] = 37057

    # AI analysis state (shared between threads)
    ai_state = {
        'analysis': "Waiting for market data...",
        'last_update': 0,
        'previous_data': None,
        'updating': False,
        'conversation_history': []  # Keep last 5 interactions
    }
    
    # Market data collection state (separate from AI)
    market_state = {
        'current_data': None,
        'last_update': 0,
        'updating': False
    }
    
    # Real BTC price state
    btc_state = {
        'price': None,
        'last_update': 0,
        'updating': False
    }
    
    # Historical price tracking for chart
    ai_price_history = []
    btc_price_history = []

    while True:
        h, w = stdscr.getmaxyx()
        stdscr.erase()
        tstamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        header = f"▓▓▓ POLYMARKET RANGE UI ▓▓▓  Event {event_id}  {tstamp}  [q: quit]"
        stdscr.addstr(0, 0, header[:max(0,w-1)], curses.color_pair(4) | curses.A_BOLD)

        # Check if market data collection needed (every 25 seconds, async)
        current_time = time.time()
        if (current_time - market_state['last_update'] >= 25 and 
            not market_state['updating']):
            market_state['updating'] = True
            # Start market data collection in background thread - combine all events
            all_brackets = brackets + additional_brackets + reach_dip_brackets
            data_thread = threading.Thread(
                target=collect_market_data_async,
                args=(all_brackets, event_id, market_state),
                daemon=True
            )
            data_thread.start()
        
        # Check if AI update needed (every 30 seconds, async) - uses latest collected data
        if (current_time - ai_state['last_update'] >= 30 and 
            not ai_state['updating'] and 
            market_state['current_data'] is not None):
            ai_state['updating'] = True
            # Start AI analysis in background thread using latest collected data
            ai_thread = threading.Thread(
                target=update_ai_analysis_async,
                args=(market_state['current_data'], ai_state['previous_data'], ai_state),
                daemon=True
            )
            ai_thread.start()
            ai_state['previous_data'] = market_state['current_data']
            ai_state['updating'] = False

        # Check if BTC price update needed (every 60 seconds, async)
        if (current_time - btc_state['last_update'] >= 60 and 
            not btc_state['updating']):
            btc_state['updating'] = True
            # Start BTC price fetch in background thread
            btc_thread = threading.Thread(
                target=update_btc_price_async,
                args=(btc_state,),
                daemon=True
            )
            btc_thread.start()

        # Extract AI price and add to history
        if ai_state['analysis'] and ai_state['analysis'] != "Waiting for market data...":
            ai_price = extract_ai_price(ai_state['analysis'])
            if ai_price and (not ai_price_history or abs(ai_price - ai_price_history[-1]) > 0.01):
                ai_price_history.append(ai_price)
                # Keep recent history (last 100 points)
                ai_price_history = ai_price_history[-100:]

        # Add BTC price to history when updated
        if btc_state['price'] and (not btc_price_history or abs(btc_state['price'] - btc_price_history[-1]) > 0.01):
            btc_price_history.append(btc_state['price'])
            btc_price_history = btc_price_history[-100:]

        # Display current AI analysis with proper wrapping  
        separator_col = min(72, w * 5 // 8)  # Separator at 5/8 width or col 72
        chart_start_col = separator_col + 3   # Chart starts 3 cols after separator
        ai_display_width = separator_col - 2
        
        # Get model and effort info from AI state
        model = ai_state.get('model', 'AI')
        effort = ai_state.get('effort', '')
        
        ai_lines = wrap_ai_text(ai_state['analysis'], ai_display_width, model, effort)
        for i, line in enumerate(ai_lines):
            if i + 1 < h:  # Make sure we don't exceed screen height
                # Split line to color the model prefix differently
                prefix_end = line.find(']> ') + 3 if ']> ' in line else 0
                if prefix_end > 0:
                    # Draw model prefix in bright green
                    stdscr.addstr(1 + i, 0, line[:prefix_end], curses.color_pair(1) | curses.A_BOLD)
                    # Draw rest in yellow with italic
                    if prefix_end < len(line):
                        stdscr.addstr(1 + i, prefix_end, line[prefix_end:ai_display_width-prefix_end], curses.color_pair(3) | curses.A_ITALIC)
                else:
                    # No prefix, just draw in yellow with italic (continuation lines)
                    stdscr.addstr(1 + i, 0, line[:ai_display_width], curses.color_pair(3) | curses.A_ITALIC)

        # Calculate header row based on AI text lines
        header_row = 1 + len(ai_lines) + 1  # 1 for main header + AI lines + 1 gap
        
        # Draw vertical separator line
        for sep_row in range(1, h-1):
            if sep_row < h-1:
                try:
                    stdscr.addstr(sep_row, separator_col, "│", curses.color_pair(4))
                except curses.error:
                    pass

        # column layout (adjusted for separator)
        lbl_w = max(18, min(35, separator_col//3))
        col_yes = lbl_w + 2
        col_no  = col_yes + 8
        col_dir = col_no + 6
        col_spk = col_dir + 5
        spk_width = separator_col - col_spk - 2  # Sparklines end before separator
        
        # headings
        stdscr.addstr(header_row, 0, "Bracket".ljust(lbl_w))
        stdscr.addstr(header_row, col_yes, "Yes")
        stdscr.addstr(header_row, col_no,  "No")
        stdscr.addstr(header_row, col_dir, "Dir")
        stdscr.addstr(header_row, col_spk, "Spark (Yes)")
        stdscr.hline(header_row + 1, 0, ord("─"), max(0, separator_col-1))

        row = header_row + 2
        
        # Display main event
        if brackets:
            stdscr.addstr(row, 0, f"Event {event_id} (Broad Ranges):", curses.color_pair(4) | curses.A_BOLD)
            row += 1
            
            for b in brackets:
                try:
                    yp = fetch_price(b["yes_token"], "buy")
                    np = fetch_price(b["no_token"],  "buy")
                except (URLError, HTTPError):
                    yp = np = None

                # update history
                if yp is not None:
                    b["yes_hist"].append(max(0.0, min(1.0, yp)))
                    b["yes_hist"] = b["yes_hist"][-hist:]
                if np is not None:
                    b["no_hist"].append(max(0.0, min(1.0, np)))
                    b["no_hist"] = b["no_hist"][-hist:]

                # direction based on Yes price
                arrow = "▬"; color = curses.color_pair(3) | curses.A_BOLD
                if b["last_yes"] is not None and yp is not None:
                    if yp > b["last_yes"] + 1e-4:
                        arrow = "▲"; color = curses.color_pair(1) | curses.A_BOLD
                    elif yp < b["last_yes"] - 1e-4:
                        arrow = "▼"; color = curses.color_pair(2) | curses.A_BOLD
                b["last_yes"] = yp if yp is not None else b["last_yes"]
                b["last_no"]  = np if np is not None else b["last_no"]

                # draw line
                label = trim_bracket_label(b["bracket"], lbl_w)
                stdscr.addstr(row, 0, label.ljust(lbl_w))
                stdscr.addstr(row, col_yes, f"{yp:.3f}".ljust(6) if yp is not None else "  n/a ")
                stdscr.addstr(row, col_no,  f"{np:.3f}".ljust(6) if np is not None else "  n/a ")
                stdscr.addstr(row, col_dir, arrow, color)
                draw_colored_spark(
                    stdscr,
                    row,
                    col_spk,
                    b["yes_hist"],
                    max(8, spk_width),
                    curses.color_pair(5) | curses.A_BOLD,  # up (green)
                    curses.color_pair(6) | curses.A_BOLD,  # down (red)
                    curses.color_pair(7)                   # flat (neutral)
                )
                row += 1
                if row >= h-8:  # Leave more room for second event and BTC price
                    break
        
        # Display additional event
        if additional_brackets and row < h-4:
            row += 1
            stdscr.addstr(row, 0, "Event 36060 (Fine Ranges):", curses.color_pair(4) | curses.A_BOLD)
            row += 1
            
            for b in additional_brackets:
                try:
                    yp = fetch_price(b["yes_token"], "buy")
                    np = fetch_price(b["no_token"],  "buy")
                except (URLError, HTTPError):
                    yp = np = None

                # update history
                if yp is not None:
                    b["yes_hist"].append(max(0.0, min(1.0, yp)))
                    b["yes_hist"] = b["yes_hist"][-hist:]
                if np is not None:
                    b["no_hist"].append(max(0.0, min(1.0, np)))
                    b["no_hist"] = b["no_hist"][-hist:]

                # direction based on Yes price
                arrow = "▬"; color = curses.color_pair(3) | curses.A_BOLD
                if b["last_yes"] is not None and yp is not None:
                    if yp > b["last_yes"] + 1e-4:
                        arrow = "▲"; color = curses.color_pair(1) | curses.A_BOLD
                    elif yp < b["last_yes"] - 1e-4:
                        arrow = "▼"; color = curses.color_pair(2) | curses.A_BOLD
                b["last_yes"] = yp if yp is not None else b["last_yes"]
                b["last_no"]  = np if np is not None else b["last_no"]

                # draw line
                label = trim_bracket_label(b["bracket"], lbl_w-5)  # Shorter for additional event
                stdscr.addstr(row, 0, label.ljust(lbl_w))
                stdscr.addstr(row, col_yes, f"{yp:.3f}".ljust(6) if yp is not None else "  n/a ")
                stdscr.addstr(row, col_no,  f"{np:.3f}".ljust(6) if np is not None else "  n/a ")
                stdscr.addstr(row, col_dir, arrow, color)
                draw_colored_spark(
                    stdscr,
                    row,
                    col_spk,
                    b["yes_hist"],
                    max(8, spk_width),
                    curses.color_pair(5) | curses.A_BOLD,  # up (green)
                    curses.color_pair(6) | curses.A_BOLD,  # down (red)
                    curses.color_pair(7)                   # flat (neutral)
                )
                row += 1
                if row >= h-6:  # Leave room for third event and BTC price
                    break
        
        # Display reach/dip event
        if reach_dip_brackets and row < h-4:
            row += 1
            stdscr.addstr(row, 0, "Event 37057 (Reach/Dip):", curses.color_pair(4) | curses.A_BOLD)
            row += 1
            
            for b in reach_dip_brackets:
                # Skip resolved dip $120k market (BTC already hit $120k)
                if "dip to $120k" in b["bracket"].lower():
                    continue
                    
                try:
                    yp = fetch_price(b["yes_token"], "buy")
                    np = fetch_price(b["no_token"],  "buy")
                except (URLError, HTTPError):
                    yp = np = None

                # update history
                if yp is not None:
                    b["yes_hist"].append(max(0.0, min(1.0, yp)))
                    b["yes_hist"] = b["yes_hist"][-hist:]
                if np is not None:
                    b["no_hist"].append(max(0.0, min(1.0, np)))
                    b["no_hist"] = b["no_hist"][-hist:]

                # direction based on Yes price
                arrow = "▬"; color = curses.color_pair(3) | curses.A_BOLD
                if b["last_yes"] is not None and yp is not None:
                    if yp > b["last_yes"] + 1e-4:
                        arrow = "▲"; color = curses.color_pair(1) | curses.A_BOLD
                    elif yp < b["last_yes"] - 1e-4:
                        arrow = "▼"; color = curses.color_pair(2) | curses.A_BOLD
                b["last_yes"] = yp if yp is not None else b["last_yes"]
                b["last_no"]  = np if np is not None else b["last_no"]

                # draw line with simplified label
                bracket_simple = b["bracket"].replace("Will Bitcoin reach ", "reach ").replace("Will Bitcoin dip to ", "dip ")
                label = trim_bracket_label(bracket_simple, lbl_w-5)
                stdscr.addstr(row, 0, label.ljust(lbl_w))
                stdscr.addstr(row, col_yes, f"{yp:.3f}".ljust(6) if yp is not None else "  n/a ")
                stdscr.addstr(row, col_no,  f"{np:.3f}".ljust(6) if np is not None else "  n/a ")
                stdscr.addstr(row, col_dir, arrow, color)
                draw_colored_spark(
                    stdscr,
                    row,
                    col_spk,
                    b["yes_hist"],
                    max(8, spk_width),
                    curses.color_pair(5) | curses.A_BOLD,  # up (green)
                    curses.color_pair(6) | curses.A_BOLD,  # down (red)
                    curses.color_pair(7)                   # flat (neutral)
                )
                row += 1
                if row >= h-2:  # Leave room for BTC price at bottom
                    break

        # Display price comparison chart on the right side
        if w > 95:  # Need wider screen since chart is further right
            chart_width = w - chart_start_col - 1  # Use almost all remaining width
            chart_height = h - header_row - 3  # Use most of remaining height, leave room for BTC price
            if chart_width > 22 and chart_height > 8:
                try:
                    draw_price_chart(stdscr, header_row, chart_start_col, 
                                   chart_width, chart_height, ai_price_history, btc_price_history)
                except curses.error:
                    pass  # Ignore drawing errors

        # Display real BTC price at bottom
        if btc_state['price'] is not None:
            btc_time = time.strftime("%H:%M:%S", time.localtime(btc_state['last_update']))
            btc_text = f"Real BTC: ${btc_state['price']:,.2f} (updated {btc_time})"
            stdscr.addstr(h-1, 0, btc_text[:w-1], curses.color_pair(1) | curses.A_BOLD)
        else:
            stdscr.addstr(h-1, 0, "Real BTC: Loading...", curses.color_pair(3))

        stdscr.refresh()
        # Original blocking timeout behavior for live feeling
        stdscr.timeout(interval*1000)
        ch = stdscr.getch()
        if ch in (ord('q'), ord('Q'), 27):  # q, Q, or ESC
            break

def cli():
    p = argparse.ArgumentParser(description="Retro terminal UI for Polymarket range markets (Yes/No pairs).")
    p.add_argument("--event", "-e", type=int, required=True, help="Event ID (e.g., 37049)")
    p.add_argument("--interval", "-i", type=int, default=3, help="Refresh interval seconds")
    p.add_argument("--history", "-H", type=int, default=30, help="Sparkline history length (samples)")
    args = p.parse_args()
    curses.wrapper(main, args.event, max(1,args.interval), max(5,args.history))

if __name__ == "__main__":
    cli()
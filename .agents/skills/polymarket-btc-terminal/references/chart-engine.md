# Chart Engine Reference — draw_price_chart()

## Function Signature

```python
def draw_price_chart(stdscr, start_row, start_col, width, height, ai_prices, btc_prices):
```

Called every frame from the main render loop, passing:
- `start_row` = 1 (just below header)
- `start_col` = separator_col + 3
- `width` = chart_width (calculated as `max(25, (w - separator_col - 4))`)
- `height` = chart_height (calculated as `max(10, h - 4)`)
- `ai_prices` = `ai_price_history[-max_points:]`
- `btc_prices` = `btc_price_history[-max_points:]`

## Internal Dimensions

```python
chart_width  = max(25, width - 5)    # nearly all available width
chart_height = max(10, height - 3)   # nearly all available height
max_points   = max(60, (chart_width - 10) * 2)  # 200% data density
plot_width   = chart_width - 4       # drawable area inside borders
```

## Rendering Pipeline (in order)

1. **Guard**: if no data → show placeholder "Price Chart" + "Collecting data..."
2. **Data prep**: slice histories to `max_points`, pad shorter series with `None`
3. **Scale**: `min_price = min(all non-None)`, `max_price = max(all non-None)`. If equal → ±100 padding.
4. **Border**: draw `┌─ PRICE COMPARISON ───┐` header
5. **Legend row**: `│ AI: ●   Real: ■         │`
6. **Max label row**: `│ $XXX,XXX              │`
7. **Divider row**: `│────────────────────────│`
8. **Grid rows**: `chart_height` rows of `│ spaces │`
9. **Bottom**: divider + min label + `└──────────────────────┘`
10. **AI points (●)**: yellow, `color_pair(3) | curses.A_BOLD`
11. **BTC points (■)**: green, `color_pair(1)`, drawn at `x + 1` (offset avoids overlap)

## Horizontal Spacing Formula

```python
x = chart_start_x + int(i * (plot_width / max(2, max_len - 1)) * 0.5)
```

The `* 0.5` factor is deliberate — packs points at 200% density vs default spacing.
**Never remove it.** It was added specifically to show more history in the visible window.

## Vertical Scaling Formula

```python
y_ratio = (price - min_price) / (max_price - min_price)  # 0.0=bottom, 1.0=top
y = chart_start_y + int((1 - y_ratio) * (chart_height - 2))  # inverted: higher price → lower row index
```

## Bounds Clamping (always apply before addstr)

```python
x = max(chart_start_x, min(x, start_col + chart_width - 3))
y = max(chart_start_y, min(y, chart_start_y + chart_height - 2))
```

## Layout Trigger

Chart only renders when:
```python
if w > 95 and chart_width > 22 and chart_height > 8:
    draw_price_chart(...)
```

## How to Add Features Inside the Chart

All additions must stay inside `draw_price_chart()`. Coordinate system:
- Top-left of chart content area: `(start_row + 1, start_col + 2)`
- Bottom-right: `(start_row + chart_height + 4, start_col + chart_width - 3)`

### Add error display (AI vs real diff)
```python
if ai_prices and btc_prices:
    error = abs(ai_prices[-1] - btc_prices[-1])
    color = curses.color_pair(2) if error > 1500 else \
            curses.color_pair(3) if error > 500 else curses.color_pair(1)
    stdscr.addstr(start_row + 2, start_col + 2, f"Err: ${error:,.0f}", color)
    # shift max label down 1 row to compensate
```

### Show more history
```python
# Increase multiplier: * 2 → * 2.5 or * 3
max_points = max(80, (chart_width - 10) * 2.5)
```

### Lower the terminal width threshold
```python
if w > 80 and ...:   # was 95
```

### Add time axis labels
- Insert at `start_row + chart_height + 5` (below bottom border)
- Show timestamps at first, middle, last data point positions

## Performance Notes

- Redraws fully every frame — acceptable for ≤100 points
- No caching — `min_price`/`max_price` recalculated each frame
- Do NOT move chart drawing to a separate thread
- Do NOT add `time.sleep()` calls inside

## History List Behavior

```python
# In main render loop (lines ~731-739):
if ai_price and (not ai_price_history or abs(ai_price - ai_price_history[-1]) > 0.01):
    ai_price_history.append(ai_price)
    ai_price_history = ai_price_history[-100:]   # cap at 100

if btc_state['price'] and (not btc_price_history or abs(btc_state['price'] - btc_price_history[-1]) > 0.01):
    btc_price_history.append(btc_state['price'])
    btc_price_history = btc_price_history[-100:]
```

The `> 0.01` filter prevents noise from micro-fluctuations. Lower it to `> 0.001` if you want smoother traces.

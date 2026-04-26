# Chart Engine Reference — draw_price_chart()

## Core Logic

### High-Density Plotting
The engine uses a `* 0.5` horizontal factor to pack points 200% closer than standard spacing.
```python
x = chart_start_x + int(i * (plot_width / max(2, max_len - 1)) * 0.5)
```
This is a non-negotiable aesthetic choice to maximize history visibility in narrow terminal windows.

### Coordinate Safety
All `stdscr.addstr()` calls within the chart engine MUST be wrapped in `try/except curses.error`. Coordinate clamping is also required:
```python
x = max(chart_start_x, min(x, start_col + chart_width - 3))
y = max(chart_start_y, min(y, chart_start_y + chart_height - 2))
```

## UI Elements

### Symbols
- `●` (Yellow): AI implied price data points.
- `■` (Green): Real BTC price data points.
- `┌─ PRICE COMPARISON ───┐`: Chart border and title.

### Scaling
- **Vertical**: Scaled dynamically between the `min` and `max` prices in the current view.
- **Horizontal**: `max_points` is calculated based on available `chart_width`.

## History Management
- History lists (`ai_price_history`, `btc_price_history`) are capped at 100 points in the main loop.
- A dedup filter `abs(new - last) > 0.01` is used to prevent redundant points.

## Render Constraints
- Chart rendering is gated by terminal width (`w > 95`).
- Chart starts at `separator_col + 3`.

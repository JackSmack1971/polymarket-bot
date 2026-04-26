# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.4.0] - 2026-04-26

### Added
- **Arbitrage Detection**: Implemented logic to detect contradictory market probabilities (e.g., Reach probabilities exceeding Range probabilities).
- **Volume-Weighted Confidence**: Added liquidity analysis to the confidence score; predictions with low volume (<$10k) now carry a "Liquidity Discount."
- **Metadata Expansion**: `PolymarketRepository` now captures real-time volume, liquidity, and expiry data for all markets.
- **Source Discrepancy Gate**: Implemented a $2,000 threshold check between Fine and Broad ranges to flag potential data divergence.

### Changed
- **System Prompt v2.5**: Refined the AI's analytical framework to explicitly prioritize arbitrage and liquidity analysis.
- **User Prompt Expansion**: Added `TOTAL_EVENT_VOLUME` and `ARBITRAGE_DETECTED` flags to the AI's real-time data snapshot.

### Fixed
- **Synthesis Math Overflow**: Fixed potential issues with non-normalized probability sums by implementing a stricter probability gate.
- **Data Gaps**: Improved handling of missing volume or liquidity data in the repository layer.

## [2.2.0] - 2026-04-26

### Added
- **Deterministic α-Tuning**: Transitioned from heuristic prompt-based smoothing to code-enforced regimes based on the new Probability Shift Index (PSI).
- **Source-Weighted EV Synthesis**: Implemented a normalized weighted ensemble (Main: 35%, Fine: 40%, Tail: 25%) in `PredictionService`.
- **Hard Move Caps**: Implemented code-level clamping ($800 for Stable, $1500 for Momentum) to prevent AI hallucinatory volatility.
- **Regime Detection**: Automated detection of market regimes (STABLE, MOMENTUM, REGIME CHANGE) passed explicitly to the AI model.

### Changed
- **Stateless Mathematical Logic**: Further refined `PredictionService` to handle multi-source EV calculations with normalized probability mass.
- **Enhanced AI Prompting**: Refined the user prompt to include explicit `PREVIOUS_ESTIMATE` and `PSI` metrics, reducing model reliance on conversational history.
- **State Management**: Expanded `AIState` to track prediction metadata across turns.

### Fixed
- **Weighting Imbalance**: Fixed issue where the source with the most brackets would disproportionately skew the implied price.
- **Hallucination Risk**: Reduced risk of AI ignoring move limits by enforcing them in the Python service layer.

## [2.1.0] - 2026-04-26

### Added
- **Real-Time Market Updates**: Implemented `MarketWorker` for continuous order book polling (15s interval), fixing the stale data issue.
- **Multi-Event Data Ingestion**: Automated structure and price fetching for fine-ranges (36060) and reach/dip (37057) markets.
- **Thread Status Dashboard**: New TUI footer bar providing real-time health and latency metrics for all background workers (AI, MKT, CG).

### Changed
- **Stateless Prediction Service**: Refactored `PredictionService` to operate on thread-safe snapshots, improving concurrency performance.
- **Enhanced Thread Safety**: Implemented `copy.deepcopy` for market state snapshots to eliminate race conditions between UI and AI threads.
- **UI Data Flow**: Centralized price updates in the `MarketWorker`, ensuring visual consistency across sparklines and tables.

### Fixed
- **Stale Price Bug**: Resolved issue where market prices were only fetched at startup and never updated in the TUI.
- **Concurrent Modification Errors**: Fixed potential crashes when iterating over market brackets during background updates.

## [2.0.0] - 2026-04-26

### Added
- **Modular R-C-S-R Architecture**: Complete decomposition of monolithic scripts into `src/` sub-packages.
- **Unified Entry Point**: New `main.py` script with support for multiple AI providers via `--provider` flag.
- **Thread-Safe State Management**: Centralized `StateManager` using atomic `threading.Lock` for all shared data.
- **Resilient API Client**: `BaseAPI` with exponential backoff, jittered retries, and centralized error handling.
- **Background Logging**: Integrated `logging` to `bot.log` for thread-level observability.
- **Data Repositories**: Specialized `PolymarketRepository` and `CoinGeckoRepository` classes.
- **Service Layer**: Dedicated `PredictionService` and `AIService` for business logic separation.

### Changed
- **Code Consolidation**: Merged duplicate logic from `poly_ui.py` and `poly_or.py` into shared services.
- **Compatibility Shims**: Replaced original entry points with lightweight shims to maintain backward compatibility.
- **Documentation**: Updated `GEMINI.md` to reflect the new architectural standards and resolved threading issues.

### Fixed
- **Race Conditions**: Resolved multiple potential race conditions by implementing strict lock-protected state updates.
- **Deadlocks**: Fixed `updating` flag management by moving resets to `finally` blocks in background workers.
- **Reliability**: Improved API stability during transient network issues through retry logic.

## [1.0.0] - 2026-04-25
- Initial release with OpenAI and OpenRouter support.
- Curses-based TUI with live market data.

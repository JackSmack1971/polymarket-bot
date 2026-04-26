"""
Evaluation Service — Performance Ledger
Logs AI implied price predictions vs actual BTC prices.
Writes append-only JSONL to performance_ledger.jsonl for backtesting.
"""
import json
import logging
import time
import threading
from pathlib import Path
from typing import Optional

_LEDGER_PATH = Path("performance_ledger.jsonl")
_lock = threading.Lock()


class EvaluationService:
    """
    Tracks the Performance Ledger:
    - log_prediction(price): record when the AI outputs a new implied price.
    - log_actual_price(price): record the live BTC price (from CoinGecko).
    - get_recent_errors(n): return the last n prediction errors (implied - actual).
    """

    @staticmethod
    def log_prediction(implied_price: float) -> None:
        """Append an AI prediction entry to the ledger."""
        record = {
            "type": "prediction",
            "timestamp": time.time(),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "implied_price": implied_price,
        }
        EvaluationService._append(record)

    @staticmethod
    def log_actual_price(actual_price: float) -> None:
        """
        Append an actual BTC price entry to the ledger.
        Also computes the error against the most recent prediction if available.
        """
        recent_prediction = EvaluationService._last_prediction()
        error = None
        if recent_prediction is not None:
            error = round(implied := recent_prediction - actual_price, 2)

        record = {
            "type": "actual",
            "timestamp": time.time(),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "actual_price": actual_price,
            "last_implied": recent_prediction,
            "prediction_error": error,
        }
        EvaluationService._append(record)

        if error is not None:
            pct = abs(error) / actual_price * 100
            logging.info(
                f"EvaluationService: Error=${error:+,.0f} ({pct:.2f}%) | "
                f"Implied=${recent_prediction:,.0f} vs Actual=${actual_price:,.0f}"
            )

    @staticmethod
    def get_recent_errors(n: int = 10) -> list:
        """
        Return the last n prediction_error values from the ledger.
        Useful for tuning α weights in PredictionService.
        """
        errors = []
        try:
            with _lock:
                if not _LEDGER_PATH.exists():
                    return []
                with _LEDGER_PATH.open("r", encoding="utf-8") as f:
                    lines = f.readlines()
            for line in reversed(lines):
                try:
                    rec = json.loads(line)
                    if rec.get("type") == "actual" and rec.get("prediction_error") is not None:
                        errors.append(rec["prediction_error"])
                        if len(errors) >= n:
                            break
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logging.warning(f"EvaluationService: Could not read ledger: {e}")
        return list(reversed(errors))

    # ──────────────────────────────── Internal ────────────────────────────────

    @staticmethod
    def _append(record: dict) -> None:
        try:
            with _lock:
                with _LEDGER_PATH.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
        except Exception as e:
            logging.error(f"EvaluationService: Failed to write ledger: {e}")

    @staticmethod
    def _last_prediction() -> Optional[float]:
        """Read the most recent prediction entry from the ledger."""
        try:
            with _lock:
                if not _LEDGER_PATH.exists():
                    return None
                with _LEDGER_PATH.open("r", encoding="utf-8") as f:
                    lines = f.readlines()
            for line in reversed(lines):
                try:
                    rec = json.loads(line)
                    if rec.get("type") == "prediction":
                        return float(rec["implied_price"])
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logging.warning(f"EvaluationService: Could not read last prediction: {e}")
        return None

#!/usr/bin/env python3
import argparse
import logging
from src.ui.terminal_ui import TerminalUI

def setup_logging():
    logging.basicConfig(
        filename='bot.log',
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(threadName)s: %(message)s'
    )
    logging.info("Polymarket Bot started.")

def main():
    parser = argparse.ArgumentParser(description="Polymarket BTC Terminal")
    parser.add_argument("--event", "-e", type=int, default=37049, help="Event ID")
    parser.add_argument("--provider", "-p", choices=["openai", "openrouter"], default="openai", help="AI Provider")
    parser.add_argument("--interval", "-i", type=int, default=3, help="Refresh interval")
    args = parser.parse_args()

    setup_logging()
    
    try:
        ui = TerminalUI(event_id=args.event, provider=args.provider, interval=args.interval)
        ui.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.critical(f"Unhandled exception in main: {e}", exc_info=True)
    finally:
        logging.info("Polymarket Bot stopped.")

if __name__ == "__main__":
    main()

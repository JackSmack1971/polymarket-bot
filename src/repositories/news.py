"""
News Repository — Market Sentiment RAG Layer
Fetches latest Bitcoin headlines from public RSS feeds.
Implements exponential backoff to comply with BFRI standards.
"""
import logging
import time
from typing import List

import feedparser

# Public BTC-relevant RSS feeds (no auth required)
_BTC_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=BTC-USD&region=US&lang=en-US",
    "https://cointelegraph.com/rss/tag/bitcoin",
    "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
]

_MAX_HEADLINES = 5
_MAX_RETRIES = 3
_BASE_DELAY = 1.0


class NewsRepository:
    @staticmethod
    def fetch_btc_headlines(max_items: int = _MAX_HEADLINES) -> List[str]:
        """
        Fetch the latest Bitcoin headlines from multiple RSS feeds.
        Returns a list of headline strings (title + source).
        Falls back gracefully if all feeds fail.
        """
        headlines: List[str] = []

        for feed_url in _BTC_FEEDS:
            if len(headlines) >= max_items:
                break
            try:
                entries = NewsRepository._fetch_feed_with_backoff(feed_url)
                for entry in entries[: max_items - len(headlines)]:
                    title = entry.get("title", "").strip()
                    if title:
                        headlines.append(title)
            except Exception as e:
                logging.warning(f"NewsRepository: Feed failed ({feed_url[:40]}...): {e}")

        if not headlines:
            logging.warning("NewsRepository: All feeds failed; returning empty headline list.")

        return headlines

    @staticmethod
    def _fetch_feed_with_backoff(url: str) -> list:
        """Fetch an RSS feed with exponential backoff on failure."""
        delay = _BASE_DELAY
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                feed = feedparser.parse(url)
                if feed.bozo and not feed.entries:
                    raise ValueError(f"Malformed feed: {feed.bozo_exception}")
                return feed.entries or []
            except Exception as e:
                if attempt == _MAX_RETRIES:
                    raise
                logging.warning(
                    f"NewsRepository: Attempt {attempt}/{_MAX_RETRIES} failed for {url[:40]}. "
                    f"Retrying in {delay:.1f}s. Error: {e}"
                )
                time.sleep(delay)
                delay *= 2
        return []

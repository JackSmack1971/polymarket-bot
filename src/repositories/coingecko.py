from src.repositories.base_api import BaseAPI
from src.core.config import COINGECKO_BASE

class CoinGeckoRepository(BaseAPI):
    @classmethod
    def fetch_btc_price(cls):
        """Fetch current BTC price from CoinGecko."""
        url = f"{COINGECKO_BASE}/simple/price?ids=bitcoin&vs_currencies=usd"
        j = cls.http_get_json(url, timeout=5)
        if j and "bitcoin" in j and "usd" in j["bitcoin"]:
            return j["bitcoin"]["usd"]
        return None

import json
import time
import random
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import logging

class BaseAPI:
    @staticmethod
    def http_get_json(url: str, timeout: int = 10, max_retries: int = 3):
        req = Request(url, headers={"User-Agent": "poly-bot/2.0"})
        
        for attempt in range(max_retries):
            try:
                with urlopen(req, timeout=timeout) as r:
                    data = r.read()
                
                decoded_data = data.decode("utf-8")
                try:
                    return json.loads(decoded_data)
                except json.JSONDecodeError:
                    # Handle raw number responses (e.g., from CLOB /price)
                    s = decoded_data.strip()
                    try:
                        return float(s)
                    except ValueError:
                        return None
                        
            except (URLError, HTTPError) as e:
                if attempt == max_retries - 1:
                    logging.error(f"Final attempt failed for {url}: {e}")
                    return None
                
                # Exponential backoff: 1s, 2s, 4s... with jitter
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                logging.warning(f"Attempt {attempt+1} failed for {url}, retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)
            except Exception as e:
                logging.error(f"Unexpected error for {url}: {e}")
                return None
        
        return None

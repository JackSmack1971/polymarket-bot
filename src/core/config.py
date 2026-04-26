import os

# API Bases
GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Hardcoded Event IDs (from original scripts)
EVENT_ID_MAIN = 37049
EVENT_ID_FINE_RANGES = 36060
EVENT_ID_REACH_DIP = 37057

# Load API keys from environment or .env file manually
def load_env():
    try:
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        pass

load_env()

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

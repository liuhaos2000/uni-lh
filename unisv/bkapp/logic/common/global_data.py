import threading
import requests
from django.conf import settings

_lock = threading.Lock()
_data = None


def get_allskname_fromapi_global():
    global _data

    if _data is None:
        with _lock:
            if _data is None:
                stock_url = f"http://api.momaapi.com/hslt/list/{settings.MOMA_TOKEN}"
                etf_url = f"http://api.momaapi.com/fd/list/etf/{settings.MOMA_TOKEN}"

                stock_data = requests.get(stock_url).json()
                etf_data = requests.get(etf_url).json()

                _data = stock_data + etf_data
                print("LH001: Fetched stock and ETF data from API and stored in global variable.")
    return _data

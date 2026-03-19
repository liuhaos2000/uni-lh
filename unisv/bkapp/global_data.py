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
                # 真正请求 API 的地方
                url = f"http://api.momaapi.com/hslt/list/{settings.MOMA_TOKEN}"
                response = requests.get(url)
                _data = response.json()
                print(11111111111)
    return _data
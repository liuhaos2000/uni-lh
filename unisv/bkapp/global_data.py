import threading
import requests

_lock = threading.Lock()
_data = None


def get_allskname_fromapi_global():
    global _data

    if _data is None:
        with _lock:
            if _data is None:
                # 真正请求 API 的地方
                url = "http://api.momaapi.com/hslt/list/34E1BB45-2D59-4761-AB47-CEBC7A676A57"
                response = requests.get(url)
                _data = response.json()
                print(11111111111)
    return _data
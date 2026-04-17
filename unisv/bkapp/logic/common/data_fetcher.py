"""ETF 数据获取公共模块。

所有策略共用的数据获取逻辑：历史日线、实时行情、ETF名称、日期校验等。
将来更换数据源只需要修改本文件。
"""
import requests as http_requests
import json
import re
from datetime import date, datetime, time as dtime
from zoneinfo import ZoneInfo
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone

from .global_data import get_allskname_fromapi_global


# ==================== 基础工具 ====================

def get_market_prefix(code):
    """根据ETF代码判断市场前缀（sh/sz）。"""
    if code.startswith(('51', '56', '58')):
        return 'sh'
    return 'sz'


def parse_date(s):
    """把 'YYYY/MM/DD' 或 'YYYY-MM-DD' 解析为 date，失败返回 None。"""
    if not s:
        return None
    s = s.strip().replace('-', '/')
    try:
        return datetime.strptime(s, '%Y/%m/%d').date()
    except ValueError:
        return None


def is_trade_day(d):
    """判断给定日期是不是 A 股交易日（排除周末和法定节假日）。"""
    if d.weekday() >= 5:
        return False
    try:
        import chinese_calendar
        return chinese_calendar.is_workday(d) and not chinese_calendar.is_holiday(d)
    except ImportError:
        return True
    except (NotImplementedError, KeyError):
        return True


def in_trading_session(now=None):
    """是否在 A 股盘中（09:30–）。"""
    now = now or timezone.localtime()
    # A股交易时间以北京时间为准，避免服务端 TIME_ZONE=UTC 导致错判
    try:
        now = now.astimezone(ZoneInfo("Asia/Shanghai"))
    except Exception:
        pass
    if not is_trade_day(now.date()):
        return False
    t = now.time()
    morning = dtime(9, 30) <= t
    return morning


# ==================== ETF 名称 ====================

def fetch_etf_names(codes):
    """查询 ETF 名称：使用 global_data 中缓存的全市场代码列表。"""
    names = {}
    try:
        allnames = get_allskname_fromapi_global()
        lookup = {item['dm'][:6]: item['mc'] for item in allnames if item.get('dm')}
    except Exception:
        lookup = {}

    for c in codes:
        names[c] = lookup.get(c[:6], c)

    return names


# ==================== 历史数据 ====================

def _fetch_realtime_bar(code):
    """通过 MOMA 实时接口获取当日临时 bar。"""
    token = getattr(settings, 'MOMA_TOKEN', '') or ''
    if not token:
        return None
    url = f'http://api.momaapi.com/fd/real/time/{code}/{token}'
    try:
        r = http_requests.get(url, timeout=5)
        payload = r.json()
        if isinstance(payload, list):
            data = payload[0] if payload else None
        elif isinstance(payload, dict):
            data = payload
        else:
            data = None
        if not data:
            return None
        open_p = float(data.get('o') or 0)
        current = float(data.get('p') or 0)
        high = float(data.get('h') or 0)
        low = float(data.get('l') or 0)
        volume = float(data.get('v') or data.get('tv') or 0)
        if current <= 0 or open_p <= 0:
            return None
        t = str(data.get('t') or '').strip()
        if not t:
            return None
        # Some responses omit the space between date and time (e.g. "2025-02-2115:29:05")
        m = re.search(r'(\d{4}-\d{2}-\d{2})', t)
        if not m:
            return None
        date_str = m.group(1).replace('-', '/')
        if not date_str:
            return None
        return [date_str, open_p, high, low, current, volume]
    except Exception:
        return None


def fetch_etf_history(code, include_realtime=True):
    """获取 ETF 历史日线数据。

    Args:
        code: ETF代码，如 '518880'
        include_realtime: 是否在交易时段叠加当前价作为今日临时 bar

    Returns:
        list: [[date_str, open, high, low, close, volume], ...]
    """
    cache_key = f"etf_hist_{code}"
    cached = cache.get(cache_key)
    if cached is not None:
        result = cached
    else:
        market = get_market_prefix(code)
        symbol = f'{market}{code}'

        url = 'https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20callback=/CN_MarketDataService.getKLineData'
        params = {
            'symbol': symbol,
            'scale': '240',
            'ma': 'no',
            'datalen': '1000',
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }

        r = http_requests.get(url, params=params, headers=headers, timeout=15)

        match = re.search(r'\[.*\]', r.text)
        if not match:
            raise Exception(f"ETF {code} 数据解析失败")

        raw_data = json.loads(match.group())

        result = []
        for item in raw_data:
            date_str = item['day'].replace('-', '/')
            result.append([
                date_str,
                float(item['open']),
                float(item['high']),
                float(item['low']),
                float(item['close']),
                float(item['volume']),
            ])

        cache.set(cache_key, result, 3600)

    if include_realtime and in_trading_session():
        rt_bar = _fetch_realtime_bar(code)
        if rt_bar is not None:
            merged = list(result)
            if merged and merged[-1][0] == rt_bar[0]:
                merged[-1] = rt_bar
            else:
                merged.append(rt_bar)
            return merged

    return result


def fetch_multi_etf_history(etf_codes, include_realtime=False):
    """批量获取多个 ETF 的历史数据。

    Returns:
        (etf_history_dict, error_response_tuple_or_None)
        成功时 error 为 None；失败时返回 (code, message) 供 view 层构造 Response。
    """
    etf_history_dict = {}
    for code in etf_codes:
        try:
            raw_data = fetch_etf_history(code, include_realtime=include_realtime)
            if not raw_data:
                return None, (400, f"ETF {code} 无历史数据，请检查代码是否正确")
            etf_history_dict[code] = raw_data
        except Exception as e:
            return None, (500, f"获取 ETF {code} 历史数据失败: {str(e)}")
    return etf_history_dict, None


def validate_date_range(etf_history_dict, start_date, end_date):
    """检查回测起止日期是否落在所有 ETF 的可用数据范围内。

    Returns:
        (ok, error_message)
    """
    s = parse_date(start_date)
    e = parse_date(end_date)
    if s is None:
        return False, f'起始日期格式错误：{start_date}（应为 YYYY/MM/DD）'
    if e is None:
        return False, f'结束日期格式错误：{end_date}（应为 YYYY/MM/DD）'
    if s > e:
        return False, f'起始日期 {start_date} 晚于结束日期 {end_date}'

    bottleneck_first_code = None
    bottleneck_first_date = None
    bottleneck_last_code = None
    bottleneck_last_date = None
    for code, rows in etf_history_dict.items():
        if not rows:
            return False, f'ETF {code} 无历史数据'
        first = parse_date(rows[0][0])
        last = parse_date(rows[-1][0])
        if first is None or last is None:
            continue
        if bottleneck_first_date is None or first > bottleneck_first_date:
            bottleneck_first_date = first
            bottleneck_first_code = code
        if bottleneck_last_date is None or last < bottleneck_last_date:
            bottleneck_last_date = last
            bottleneck_last_code = code

    if bottleneck_first_date and s < bottleneck_first_date:
        return False, (
            f'起始日期 {start_date} 早于可用数据范围。'
            f'ETF {bottleneck_first_code} 最早只到 {bottleneck_first_date.strftime("%Y/%m/%d")}，'
            f'请把起始日期调到该日期之后，或从 ETF 列表中移除该标的。'
        )
    if bottleneck_last_date and s > bottleneck_last_date:
        return False, (
            f'起始日期 {start_date} 晚于可用数据范围。'
            f'ETF {bottleneck_last_code} 数据只到 {bottleneck_last_date.strftime("%Y/%m/%d")}。'
        )
    return True, None

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


# ==================== ETF 名称字典 ====================

ETF_NAME_DICT = {
    # 黄金 / 商品
    '518880': '黄金ETF华安',
    '518800': '黄金基金',
    '159934': '黄金ETF',
    '159937': '博时黄金',
    '159812': '黄金ETF基金',
    '518660': '金ETF',
    # 宽基
    '510300': '沪深300ETF',
    '510500': '中证500ETF',
    '510050': '上证50ETF',
    '159915': '创业板ETF',
    '159901': '深100ETF',
    '588000': '科创50ETF',
    '588080': '科创板50ETF',
    '560010': '中证2000ETF',
    '159845': '中证2000ETF基金',
    '159922': '中证500ETF基金',
    '510330': '沪深300',
    '159919': '沪深300ETF基金',
    # 跨境 / 海外
    '513100': '纳指ETF',
    '513300': '标普ETF',
    '513500': '标普500ETF',
    '159941': '纳指ETF基金',
    '164824': '印度基金LOF',
    '513520': '日经ETF',
    '513880': '日经225ETF',
    '159866': '日经225',
    '513030': '德国DAX',
    '513080': '法国CAC40',
    '159920': '恒生ETF',
    '513060': '恒生医疗ETF',
    '159792': '越南ETF',
    '513660': '恒生科技ETF',
    '513180': '恒生科技指数ETF',
    '159605': '中概互联ETF',
    '513050': '中概互联网ETF',
    # 行业 / 主题
    '512010': '医药ETF',
    '512170': '医疗ETF',
    '515030': '新能源车ETF',
    '516160': '新能源ETF',
    '515790': '光伏ETF',
    '512480': '半导体ETF',
    '159995': '芯片ETF',
    '512760': '国泰芯片ETF',
    '512690': '酒ETF',
    '515880': '通信ETF',
    '515050': '5GETF',
    '512980': '传媒ETF',
    '512800': '银行ETF',
    '512070': '非银ETF',
    '512200': '地产ETF',
    '512580': '环保ETF',
    '512660': '军工ETF',
    '512400': '有色金属ETF',
    '515220': '煤炭ETF',
    '516780': '稀土ETF',
    '159825': '农业ETF',
    '512880': '证券ETF',
    '159869': '游戏ETF',
    '159819': '人工智能ETF',
    '515230': '软件ETF',
    '512100': '中证1000ETF',
    # 债券 / 货币
    '511010': '国债ETF',
    '511260': '十年国债ETF',
    '511020': '活跃国债ETF',
    '159972': '5年地方债ETF',
    '511380': '可转债ETF',
    '511880': '银华日利',
    '511660': '货币ETF',
    # 红利 / 价值
    '510880': '红利ETF',
    '159905': '深证红利ETF',
    '563020': '中证红利低波',
    '515180': '红利低波100ETF',
}


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
    """是否在 A 股盘中（09:30–11:30 + 13:00–15:00）。"""
    now = now or timezone.localtime()
    # A股交易时间以北京时间为准，避免服务端 TIME_ZONE=UTC 导致错判
    try:
        now = now.astimezone(ZoneInfo("Asia/Shanghai"))
    except Exception:
        pass
    if not is_trade_day(now.date()):
        return False
    t = now.time()
    morning = dtime(9, 30) <= t <= dtime(11, 30)
    afternoon = dtime(13, 0) <= t < dtime(15, 0)
    return morning or afternoon


# ==================== ETF 名称 ====================

def fetch_etf_names(codes):
    """查询 ETF 名称：优先静态字典，未命中的尝试新浪接口。"""
    names = {}
    missing = []
    for c in codes:
        if c in ETF_NAME_DICT:
            names[c] = ETF_NAME_DICT[c]
        else:
            missing.append(c)

    if missing:
        symbols = [f'{get_market_prefix(c)}{c}' for c in missing]
        url = f'https://hq.sinajs.cn/list={",".join(symbols)}'
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://finance.sina.com.cn',
        }
        try:
            r = http_requests.get(url, headers=headers, timeout=5)
            for line in r.text.strip().split('\n'):
                m = re.match(r'var hq_str_(\w+)="([^"]*)"', line.strip())
                if m:
                    full_symbol = m.group(1)
                    code = full_symbol[2:]
                    fields = m.group(2).split(',')
                    if fields and fields[0]:
                        names[code] = fields[0]
        except Exception:
            pass

    for c in codes:
        if c not in names:
            names[c] = c

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

"""多维条件策略 HTTP 接口（v2）。

endpoint: /multidim/backtest (GET)

参数：
    stock_code           股票代码（必填，单只）
    start_date / end_date 'YYYY/MM/DD'
    initial_capital

    trend_enabled / trend_short_period / trend_long_period
    momentum_enabled / momentum_period
    volprice_enabled / volprice_ratio_period / volprice_flow_period / volprice_ratio_threshold
    risk_enabled / risk_lookback / risk_drawdown_threshold
"""
import time
from datetime import datetime, timedelta

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..logic.common.global_data import get_allskname_fromapi_global
from ..logic.multidim.multidim_backtest import run_multidim_backtest
from ..utils.usage import (
    QuotaExceeded,
    VIP_INFO,
    check_and_inc_backtest,
)


def _resolve_start_str(start_date_str, fallback_years=3, warmup_days=365):
    """根据用户填写的回测开始日期推算行情拉取的 st 日期。

    多取 warmup_days 天给 MA60 / 动量60 等长周期指标做 warmup。
    解析失败时回退为"今天往前 fallback_years 年"。
    """
    today = datetime.today()
    if start_date_str:
        for fmt in ('%Y/%m/%d', '%Y-%m-%d'):
            try:
                start_dt = datetime.strptime(start_date_str, fmt)
                start_dt = start_dt - timedelta(days=warmup_days)
                return start_dt.strftime('%Y%m%d')
            except ValueError:
                continue
    return (today - timedelta(days=365 * fallback_years)).strftime('%Y%m%d')


def fetch_stock_history(stock_code, start_date_str=None):
    """日线 OHLCV，返回 [[date,o,h,l,c,v], ...]。

    根据 start_date_str 自动决定拉取起点；若未提供，默认回看 3 年。
    """
    today = datetime.today()
    end_str = today.strftime('%Y%m%d')
    start_str = _resolve_start_str(start_date_str)

    url = (
        f"http://api.momaapi.com/hsstock/history/"
        f"{stock_code}/d/n/{settings.MOMA_TOKEN}"
        f"?st={start_str}&et={end_str}&lt=2500"
    )
    r = requests.get(url, timeout=20)
    try:
        data = r.json()
    except Exception:
        raise Exception(f"行情数据接口异常：{r.text[:100]}")
    if isinstance(data, str) or not isinstance(data, list):
        raise Exception(f"行情数据接口返回错误：{str(data)[:100]}")

    out = []
    for item in data:
        try:
            date = datetime.strptime(item["t"], "%Y-%m-%d %H:%M:%S").strftime("%Y/%m/%d")
        except Exception:
            t = str(item.get("t", ""))[:10]
            if not t:
                continue
            date = t.replace('-', '/')
        out.append([
            date,
            float(item.get("o", 0) or 0),
            float(item.get("h", 0) or 0),
            float(item.get("l", 0) or 0),
            float(item.get("c", 0) or 0),
            float(item.get("v", 0) or 0),
        ])
    return out


# ── 指数行情 + 进程内缓存 ────────────────────────────────

# {full_code: (timestamp, {date: close})}，进程内 1 小时缓存
_INDEX_CACHE = {}
_INDEX_CACHE_TTL = 3600

# 常用指数：UI 选项 → 完整代码
INDEX_OPTIONS = {
    '000300.SH': '沪深300',
    '000001.SH': '上证综指',
    '000905.SH': '中证500',
    '000852.SH': '中证1000',
    '000016.SH': '上证50',
    '399006.SZ': '创业板指',
    '399001.SZ': '深证成指',
}


def _normalize_index_code(raw):
    """补齐市场后缀。'000300' → '000300.SH'；'399006' → '399006.SZ'。已含后缀的原样返回。"""
    s = (raw or '').strip().upper()
    if not s:
        return ''
    if '.' in s:
        return s
    if s.startswith('399'):
        return s + '.SZ'
    return s + '.SH'


def fetch_index_history(index_code, start_date_str=None):
    """日线指数。返回 {date: close}（date 格式 'YYYY/MM/DD'）。

    根据 start_date_str 自动决定拉取起点；若未提供，默认回看 3 年。
    """
    code = _normalize_index_code(index_code)
    today = datetime.today()
    end_str = today.strftime('%Y%m%d')
    start_str = _resolve_start_str(start_date_str)

    url = (
        f"http://api.momaapi.com/hsindex/history/"
        f"{code}/d/{settings.MOMA_TOKEN}"
        f"?st={start_str}&et={end_str}"
    )
    r = requests.get(url, timeout=20)
    try:
        data = r.json()
    except Exception:
        raise Exception(f"指数行情接口异常：{r.text[:100]}")
    if isinstance(data, str) or not isinstance(data, list):
        raise Exception(f"指数行情接口返回错误：{str(data)[:100]}")

    out = {}
    for item in data:
        try:
            date = datetime.strptime(item["t"], "%Y-%m-%d %H:%M:%S").strftime("%Y/%m/%d")
        except Exception:
            t = str(item.get("t", ""))[:10]
            if not t:
                continue
            date = t.replace('-', '/')
        try:
            out[date] = float(item.get("c", 0) or 0)
        except (TypeError, ValueError):
            continue
    return out


def get_index_history_cached(index_code, start_date_str=None):
    """进程内缓存（同一指数+起点 1 小时内只拉一次，所有标的回测共用）。"""
    code = _normalize_index_code(index_code)
    start_str = _resolve_start_str(start_date_str)
    cache_key = f'{code}|{start_str}'
    now = time.time()
    cached = _INDEX_CACHE.get(cache_key)
    if cached and (now - cached[0] < _INDEX_CACHE_TTL):
        return cached[1]
    data = fetch_index_history(code, start_date_str=start_date_str)
    _INDEX_CACHE[cache_key] = (now, data)
    return data


def align_market_to_stock(market_dict, stock_history):
    """把 {date: close} 对齐到 stock_history 的日期顺序，前向填充缺失日期。

    返回 list[float|None]，长度等于 stock_history。开始日早于指数有数据时为 None。
    """
    out = []
    last = None
    for row in stock_history:
        d = row[0]
        v = market_dict.get(d)
        if v is not None:
            last = v
        out.append(last)
    return out


# ── 标的名称解析 ─────────────────────────────────────

def _resolve_stock_name(code):
    try:
        allnames = get_allskname_fromapi_global()
        for item in allnames:
            if item.get('dm', '')[:6] == code[:6]:
                return item.get('mc', code)
    except Exception:
        pass
    return code


def _parse_bool(v, default=False):
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ('1', 'true', 'yes', 'on')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def multidim_backtest(request):
    """多维条件策略回测（v2 维度）。"""
    try:
        check_and_inc_backtest(request.user)
    except QuotaExceeded as qe:
        return Response({
            "code": 4001,
            "message": str(qe),
            "vip_info": VIP_INFO,
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        q = request.query_params
        stock_code = (q.get('stock_code') or '').strip()
        if not stock_code:
            return Response({"code": 400, "message": "stock_code 不能为空"},
                            status=status.HTTP_400_BAD_REQUEST)

        today_str = datetime.today().strftime('%Y/%m/%d')
        start_date = q.get('start_date', '2024/01/01')
        end_date = q.get('end_date', today_str)
        initial_capital = float(q.get('initial_capital', 1000000))

        # 趋势
        trend_enabled = _parse_bool(q.get('trend_enabled'), True)
        trend_short_period = int(q.get('trend_short_period', 20))
        trend_long_period = int(q.get('trend_long_period', 60))

        # 动量
        momentum_enabled = _parse_bool(q.get('momentum_enabled'), True)
        momentum_period = int(q.get('momentum_period', 60))

        # 量价
        volprice_enabled = _parse_bool(q.get('volprice_enabled'), True)
        volprice_ratio_period = int(q.get('volprice_ratio_period', 20))
        volprice_flow_period = int(q.get('volprice_flow_period', 5))
        volprice_ratio_threshold = float(q.get('volprice_ratio_threshold', 0.9))

        # 风控
        risk_enabled = _parse_bool(q.get('risk_enabled'), True)
        risk_lookback = int(q.get('risk_lookback', 60))
        risk_drawdown_threshold = float(q.get('risk_drawdown_threshold', 0.08))
        risk_mode = (q.get('risk_mode') or 'fixed').strip().lower()
        if risk_mode not in ('fixed', 'atr'):
            risk_mode = 'fixed'
        risk_atr_k = float(q.get('risk_atr_k', 2.0))

        # 合成模式：min_match_count 缺省或 0 表示 AND（全部满足）
        raw_min = q.get('min_match_count')
        if raw_min in (None, '', '0'):
            min_match_count = None
        else:
            try:
                v = int(raw_min)
                min_match_count = v if v >= 1 else None
            except ValueError:
                min_match_count = None

        # 跟踪止损
        trailing_stop_enabled = _parse_bool(q.get('trailing_stop_enabled'), False)
        trail_pct = float(q.get('trail_pct', 0.10))
        if not (0.01 <= trail_pct <= 0.5):
            return Response({"code": 400, "message": "跟踪止损幅度需在 1%-50% 之间"},
                            status=status.HTTP_400_BAD_REQUEST)
        trail_mode = (q.get('trail_mode') or 'fixed').strip().lower()
        if trail_mode not in ('fixed', 'atr'):
            trail_mode = 'fixed'
        trail_atr_k = float(q.get('trail_atr_k', 3.0))

        # ATR 共享周期
        atr_period = int(q.get('atr_period', 14))
        if not (2 <= atr_period <= 60):
            return Response({"code": 400, "message": "ATR 周期需在 2-60 之间"},
                            status=status.HTTP_400_BAD_REQUEST)
        if not (0.1 <= risk_atr_k <= 10):
            return Response({"code": 400, "message": "风控 ATR 倍数需在 0.1-10 之间"},
                            status=status.HTTP_400_BAD_REQUEST)
        if not (0.1 <= trail_atr_k <= 10):
            return Response({"code": 400, "message": "止损 ATR 倍数需在 0.1-10 之间"},
                            status=status.HTTP_400_BAD_REQUEST)

        # 市场过滤
        market_filter_enabled = _parse_bool(q.get('market_filter_enabled'), False)
        market_index = (q.get('market_index') or '000300.SH').strip()
        market_ma_period = int(q.get('market_ma_period', 60))
        if not (2 <= market_ma_period <= 250):
            return Response({"code": 400, "message": "市场过滤 MA 周期需在 2-250 之间"},
                            status=status.HTTP_400_BAD_REQUEST)

        # 校验
        if not (2 <= trend_short_period < trend_long_period <= 250):
            return Response({"code": 400, "message": "趋势均线参数非法：需 2 ≤ short < long ≤ 250"},
                            status=status.HTTP_400_BAD_REQUEST)
        if not (2 <= momentum_period <= 250):
            return Response({"code": 400, "message": "动量周期需在 2-250 之间"},
                            status=status.HTTP_400_BAD_REQUEST)
        if not (2 <= volprice_ratio_period <= 250) or not (1 <= volprice_flow_period <= 60) \
                or not (0.1 <= volprice_ratio_threshold <= 10):
            return Response({"code": 400, "message": "量价参数非法"},
                            status=status.HTTP_400_BAD_REQUEST)
        if not (5 <= risk_lookback <= 250) or not (0.01 <= risk_drawdown_threshold <= 0.5):
            return Response({"code": 400, "message": "风控参数非法：lookback 5-250，回撤阈值 1%-50%"},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            history = fetch_stock_history(stock_code, start_date_str=start_date)
        except Exception as e:
            return Response({"code": 500, "message": f"获取 {stock_code} 历史数据失败: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if not history:
            return Response({"code": 400, "message": f"{stock_code} 无历史数据"},
                            status=status.HTTP_400_BAD_REQUEST)

        # 市场过滤数据：拉指数 + 对齐到股票日期
        market_closes = None
        if market_filter_enabled:
            try:
                idx_dict = get_index_history_cached(market_index, start_date_str=start_date)
                market_closes = align_market_to_stock(idx_dict, history)
            except Exception as e:
                return Response({
                    "code": 500,
                    "message": f"获取指数 {market_index} 失败: {str(e)}",
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        result = run_multidim_backtest(
            stock_history=history,
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            trend_enabled=trend_enabled,
            trend_short_period=trend_short_period,
            trend_long_period=trend_long_period,
            momentum_enabled=momentum_enabled,
            momentum_period=momentum_period,
            volprice_enabled=volprice_enabled,
            volprice_ratio_period=volprice_ratio_period,
            volprice_flow_period=volprice_flow_period,
            volprice_ratio_threshold=volprice_ratio_threshold,
            risk_enabled=risk_enabled,
            risk_lookback=risk_lookback,
            risk_drawdown_threshold=risk_drawdown_threshold,
            risk_mode=risk_mode,
            risk_atr_k=risk_atr_k,
            min_match_count=min_match_count,
            trailing_stop_enabled=trailing_stop_enabled,
            trail_pct=trail_pct,
            trail_mode=trail_mode,
            trail_atr_k=trail_atr_k,
            atr_period=atr_period,
            market_filter_enabled=market_filter_enabled,
            market_closes=market_closes,
            market_ma_period=market_ma_period,
        )

        # 把当前选用的指数信息回传，供前端展示
        if market_filter_enabled:
            result.setdefault('summary', {})['market_index'] = _normalize_index_code(market_index)
            result['summary']['market_index_name'] = INDEX_OPTIONS.get(
                _normalize_index_code(market_index), market_index
            )

        result['stock_name'] = _resolve_stock_name(stock_code)

        return Response({"code": 0, "message": "success", "data": result})

    except Exception as e:
        return Response({"code": 500, "message": f"回测执行失败: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

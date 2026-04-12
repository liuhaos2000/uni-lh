from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

import requests as http_requests
import json
import re
from datetime import date, datetime, time as dtime
from django.core.cache import cache
from django.utils import timezone

from ..logic.momentum.rotation_backtest import run_rotation_backtest
from ..models.momentum_watch import MomentumWatch
from ..utils.usage import (
    check_and_inc_backtest, require_vip,
    QuotaExceeded, VipRequired, VIP_INFO,
)


def fetch_etf_names(codes):
    """通过新浪实时行情接口批量获取 ETF 名称。

    Args:
        codes: ETF代码列表，如 ['518880', '513100']

    Returns:
        dict: {code: name}，如 {'518880': '黄金ETF华安'}
    """
    symbols = [f'{_get_market_prefix(c)}{c}' for c in codes]
    url = f'https://hq.sinajs.cn/list={",".join(symbols)}'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://finance.sina.com.cn',
    }

    names = {}
    try:
        r = http_requests.get(url, headers=headers, timeout=10)
        for line in r.text.strip().split('\n'):
            # var hq_str_sh518880="黄金ETF华安,..."
            m = re.match(r'var hq_str_(\w+)="([^"]*)"', line.strip())
            if m:
                full_symbol = m.group(1)
                code = full_symbol[2:]  # 去掉 sh/sz
                fields = m.group(2).split(',')
                if fields:
                    names[code] = fields[0]
    except Exception:
        pass

    # 没取到名称的用代码兜底
    for c in codes:
        if c not in names:
            names[c] = c

    return names


def _get_market_prefix(code):
    """根据ETF代码判断市场前缀（sh/sz）。"""
    # 沪市ETF: 51xxxx, 56xxxx, 58xxxx
    # 深市ETF: 15xxxx, 16xxxx
    if code.startswith(('51', '56', '58')):
        return 'sh'
    else:
        return 'sz'


def _is_trade_day(d: date) -> bool:
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


def _in_trading_session(now: datetime = None) -> bool:
    """是否在 A 股盘中（含午休前后），用于决定是否要叠加实时 bar。

    时间窗口：09:30–11:30 + 13:00–15:00（含 14:57 收盘集合）。
    收盘后（>=15:00）当天日线已落库，无需叠加。
    """
    now = now or timezone.localtime()
    if not _is_trade_day(now.date()):
        return False
    t = now.time()
    morning = dtime(9, 30) <= t <= dtime(11, 30)
    afternoon = dtime(13, 0) <= t < dtime(15, 0)
    return morning or afternoon


def _fetch_realtime_bar(code):
    """通过 sinajs 实时接口获取当日临时 bar，构造 [date, open, high, low, close, volume]。

    返回 None 表示拿不到有效数据（停牌/未开盘/接口异常）。
    """
    symbol = f'{_get_market_prefix(code)}{code}'
    url = f'https://hq.sinajs.cn/list={symbol}'
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': 'https://finance.sina.com.cn',
    }
    try:
        r = http_requests.get(url, headers=headers, timeout=5)
        m = re.match(r'var hq_str_\w+="([^"]*)"', r.text.strip())
        if not m:
            return None
        fields = m.group(1).split(',')
        # sinajs 字段：name,open,prev_close,current,high,low,...,volume(8),amount(9),...,date(30),time(31)
        if len(fields) < 32:
            return None
        open_p = float(fields[1] or 0)
        current = float(fields[3] or 0)
        high = float(fields[4] or 0)
        low = float(fields[5] or 0)
        volume = float(fields[8] or 0)
        if current <= 0 or open_p <= 0:
            # 停牌或还未开盘
            return None
        date_str = (fields[30] or '').replace('-', '/')
        if not date_str:
            return None
        return [date_str, open_p, high, low, current, volume]
    except Exception:
        return None


def fetch_etf_history(code, include_realtime=False):
    """通过新浪财经接口获取 ETF 历史日线数据。

    Args:
        code: ETF代码，如 '518880'
        include_realtime: 是否在交易时段叠加当前价作为今日临时 bar。
            - 信号推送 / 回测页面：True
            - 参数优化：False（保持纯历史，结果可复现）

    Returns:
        list: [(date_str, open, high, low, close, volume), ...]
              date_str 格式为 'YYYY/MM/DD'
    """
    cache_key = f"etf_hist_{code}"
    cached = cache.get(cache_key)
    if cached is not None:
        result = cached
    else:
        market = _get_market_prefix(code)
        symbol = f'{market}{code}'

        url = 'https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20callback=/CN_MarketDataService.getKLineData'
        params = {
            'symbol': symbol,
            'scale': '240',   # 日线
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

        # 历史数据缓存1小时
        cache.set(cache_key, result, 3600)

    # 盘中实时叠加：在副本上 merge，不污染缓存
    if include_realtime and _in_trading_session():
        rt_bar = _fetch_realtime_bar(code)
        if rt_bar is not None:
            merged = list(result)
            if merged and merged[-1][0] == rt_bar[0]:
                merged[-1] = rt_bar          # 同日替换
            else:
                merged.append(rt_bar)        # 追加为今日临时 bar
            return merged

    return result


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def momentum_backtest(request):
    """动量轮动回测接口。

    Query params:
        codes: ETF代码列表，逗号分隔，如 '518880,513100,510300,159915'
        start_date: 回测起始日期，格式 'YYYY/MM/DD'
        lookback_n: 动量回看天数（1-60），默认25
        rebalance_days: 调仓周期（交易日），默认5
        initial_capital: 初始资金，默认1000000
    """
    # 非 VIP 配额检查
    try:
        check_and_inc_backtest(request.user)
    except QuotaExceeded as qe:
        return Response({
            "code": 4001,
            "message": str(qe),
            "vip_info": VIP_INFO,
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        from datetime import datetime as dt
        codes_str = request.query_params.get('codes', '518880,513100,510300,159915')
        start_date = request.query_params.get('start_date', '2024/01/01')
        end_date = request.query_params.get('end_date', dt.today().strftime('%Y/%m/%d'))
        lookback_n = int(request.query_params.get('lookback_n', 25))
        rebalance_days = int(request.query_params.get('rebalance_days', 5))
        initial_capital = float(request.query_params.get('initial_capital', 1000000))

        # 参数校验
        if lookback_n < 1 or lookback_n > 60:
            return Response({"code": 400, "message": "lookback_n 需在 1-60 之间"},
                            status=status.HTTP_400_BAD_REQUEST)

        etf_codes = [c.strip() for c in codes_str.split(',') if c.strip()]
        if len(etf_codes) < 2:
            return Response({"code": 400, "message": "至少需要2个ETF标的"},
                            status=status.HTTP_400_BAD_REQUEST)

        # 获取每个ETF的历史数据（新浪财经）
        # 回测：盘中叠加实时价作为今日临时 bar，便于实时观察当日信号
        etf_history_dict = {}
        for code in etf_codes:
            try:
                raw_data = fetch_etf_history(code, include_realtime=True)
                if not raw_data:
                    return Response({
                        "code": 400,
                        "message": f"ETF {code} 无历史数据，请检查代码是否正确"
                    }, status=status.HTTP_400_BAD_REQUEST)
                etf_history_dict[code] = raw_data
            except Exception as e:
                return Response({
                    "code": 500,
                    "message": f"获取 ETF {code} 历史数据失败: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 获取ETF名称
        etf_names = fetch_etf_names(etf_codes)

        # 执行回测
        result = run_rotation_backtest(
            etf_history_dict=etf_history_dict,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            lookback_n=lookback_n,
            rebalance_days=rebalance_days,
        )

        result['etf_names'] = etf_names

        return Response({
            "code": 0,
            "message": "success",
            "data": result,
        })

    except Exception as e:
        return Response({
            "code": 500,
            "message": f"回测执行失败: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def momentum_optimize(request):
    """参数优化：遍历 lookback_n 和 rebalance_days 组合，返回各组合的夏普比率和收益率。

    Query params:
        codes: ETF代码列表，逗号分隔
        start_date: 回测起始日期
        end_date: 回测结束日期
        initial_capital: 初始资金，默认1000000
        n_list: 回看天数列表，逗号分隔，默认 '20,21,22,23,24,25,26,27,28,29,30'
        r_list: 调仓周期列表，逗号分隔，默认 '1,2,3,4,5,6,7,8,9,10'
    """
    # 非 VIP 配额检查（参数优化和回测共用一个 quota）
    try:
        check_and_inc_backtest(request.user)
    except QuotaExceeded as qe:
        return Response({
            "code": 4001,
            "message": str(qe),
            "vip_info": VIP_INFO,
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        from datetime import datetime as dt
        codes_str = request.query_params.get('codes', '518880,513100,510300,159915')
        start_date = request.query_params.get('start_date', '2024/01/01')
        end_date = request.query_params.get('end_date', dt.today().strftime('%Y/%m/%d'))
        initial_capital = float(request.query_params.get('initial_capital', 1000000))
        n_list_str = request.query_params.get('n_list', '20,21,22,23,24,25,26,27,28,29,30')
        r_list_str = request.query_params.get('r_list', '1,2,3,4,5,6,7,8,9,10')

        n_list = [int(x.strip()) for x in n_list_str.split(',') if x.strip()]
        r_list = [int(x.strip()) for x in r_list_str.split(',') if x.strip()]

        etf_codes = [c.strip() for c in codes_str.split(',') if c.strip()]
        if len(etf_codes) < 2:
            return Response({"code": 400, "message": "至少需要2个ETF标的"},
                            status=status.HTTP_400_BAD_REQUEST)

        # 获取数据（只拉一次，复用缓存）
        etf_history_dict = {}
        for code in etf_codes:
            try:
                raw_data = fetch_etf_history(code)
                if not raw_data:
                    return Response({"code": 400, "message": f"ETF {code} 无历史数据"},
                                    status=status.HTTP_400_BAD_REQUEST)
                etf_history_dict[code] = raw_data
            except Exception as e:
                return Response({"code": 500, "message": f"获取 {code} 失败: {str(e)}"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 遍历组合
        results = []
        best = None
        for n in n_list:
            for r in r_list:
                result = run_rotation_backtest(
                    etf_history_dict=etf_history_dict,
                    start_date=start_date,
                    end_date=end_date,
                    initial_capital=initial_capital,
                    lookback_n=n,
                    rebalance_days=r,
                )
                summary = result.get('summary', {})
                row = {
                    "lookback_n": n,
                    "rebalance_days": r,
                    "total_return": summary.get('total_return', 0),
                    "sharpe_ratio": summary.get('sharpe_ratio', 0),
                    "total_trades": summary.get('total_trades', 0),
                    "final_equity": summary.get('final_equity', 0),
                }
                results.append(row)
                if best is None or row['sharpe_ratio'] > best['sharpe_ratio']:
                    best = row

        return Response({
            "code": 0,
            "message": "success",
            "data": {
                "results": results,
                "best": best,
                "n_list": n_list,
                "r_list": r_list,
            }
        })

    except Exception as e:
        return Response({"code": 500, "message": f"参数优化失败: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def momentum_subscription(request):
    """动量轮动信号订阅管理（需要登录）。

    GET    返回当前用户的订阅
    POST   body: {etf_codes, lookback_n, rebalance_days, initial_capital}
    DELETE 取消订阅
    """
    user = request.user

    if request.method == 'GET':
        watch = MomentumWatch.objects.filter(user=user).first()
        if not watch:
            return Response({"code": 0, "data": {"subscribed": False}})
        data = watch.to_dict()
        data['subscribed'] = True
        return Response({"code": 0, "data": data})

    if request.method == 'DELETE':
        MomentumWatch.objects.filter(user=user).delete()
        return Response({"code": 0, "message": "已取消订阅"})

    # POST: 创建或更新（仅 VIP 可订阅）
    try:
        require_vip(user)
    except VipRequired as ve:
        return Response({
            "code": 4002,
            "message": str(ve),
            "vip_info": VIP_INFO,
        }, status=status.HTTP_403_FORBIDDEN)

    payload = request.data or {}
    etf_codes = payload.get('etf_codes') or []
    if isinstance(etf_codes, str):
        etf_codes = [c.strip() for c in etf_codes.split(',') if c.strip()]
    if len(etf_codes) < 2:
        return Response({"code": 400, "message": "至少需要2个ETF标的"},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        lookback_n = int(payload.get('lookback_n', 25))
        rebalance_days = int(payload.get('rebalance_days', 5))
        initial_capital = float(payload.get('initial_capital', 1000000))
    except (TypeError, ValueError):
        return Response({"code": 400, "message": "参数格式错误"},
                        status=status.HTTP_400_BAD_REQUEST)

    if lookback_n < 1 or lookback_n > 60:
        return Response({"code": 400, "message": "lookback_n 需在 1-60 之间"},
                        status=status.HTTP_400_BAD_REQUEST)

    watch, created = MomentumWatch.objects.update_or_create(
        user=user,
        defaults={
            'etf_codes': etf_codes,
            'lookback_n': lookback_n,
            'rebalance_days': rebalance_days,
            'initial_capital': initial_capital,
            'enabled': True,
        },
    )
    data = watch.to_dict()
    data['subscribed'] = True
    return Response({
        "code": 0,
        "message": "订阅成功" if created else "订阅已更新",
        "data": data,
    })


@api_view(['GET'])
def etf_name_lookup(request):
    """查询ETF名称。

    Query params:
        codes: ETF代码，逗号分隔，如 '518880,513100'
    """
    codes_str = request.query_params.get('codes', '')
    codes = [c.strip() for c in codes_str.split(',') if c.strip()]
    if not codes:
        return Response({"code": 400, "message": "codes 不能为空"},
                        status=status.HTTP_400_BAD_REQUEST)

    names = fetch_etf_names(codes)
    return Response({"code": 0, "data": names})

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from ..logic.momentum.rotation_backtest import run_rotation_backtest
from ..logic.meanrev.meanrev_backtest import run_meanrev_backtest
from ..logic.common.data_fetcher import (
    fetch_etf_history, fetch_etf_names, validate_date_range,
)
from ..logic.common.metrics import build_summary
from ..utils.usage import (
    check_and_inc_backtest, QuotaExceeded, VIP_INFO,
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def combo_backtest(request):
    """组合策略回测。

    POST body (JSON):
    {
        "start_date": "2024/01/01",
        "end_date": "2026/04/13",
        "initial_capital": 1000000,
        "s1_weight": 0.5,

        "s1_type": "momentum",
        "s1_codes": ["518880","513100","510300","159915"],
        "s1_params": {
            "lookback_n": 25,
            "rebalance_days": 5
        },

        "s2_type": "meanrev",
        "s2_codes": ["518880","513100"],
        "s2_params": {
            "signal_type": "bollinger",
            "period": 20,
            "num_std": 2.0,
            "stop_loss": 0.05,
            "rebalance_days": 1,
            "oversold": 30,
            "overbought": 70
        }
    }
    """
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
        body = request.data or {}

        start_date = body.get('start_date', '2024/01/01')
        end_date = body.get('end_date', dt.today().strftime('%Y/%m/%d'))
        initial_capital = float(body.get('initial_capital', 1000000))
        s1_weight = float(body.get('s1_weight', 0.5))
        s2_weight = 1.0 - s1_weight

        s1_type = body.get('s1_type', 'momentum')
        s1_codes = body.get('s1_codes', [])
        s1_params = body.get('s1_params', {})

        s2_type = body.get('s2_type', 'meanrev')
        s2_codes = body.get('s2_codes', [])
        s2_params = body.get('s2_params', {})

        if not s1_codes or not s2_codes:
            return Response({"code": 400, "message": "两个策略都需要至少设置标的"},
                            status=status.HTTP_400_BAD_REQUEST)

        s1_capital = initial_capital * s1_weight
        s2_capital = initial_capital * s2_weight

        # 拉取所有需要的 ETF 数据
        all_codes = list(set(s1_codes + s2_codes))
        all_history = {}
        for code in all_codes:
            try:
                raw_data = fetch_etf_history(code, include_realtime=True)
                if not raw_data:
                    return Response({
                        "code": 400,
                        "message": f"ETF {code} 无历史数据"
                    }, status=status.HTTP_400_BAD_REQUEST)
                all_history[code] = raw_data
            except Exception as e:
                return Response({
                    "code": 500,
                    "message": f"获取 ETF {code} 失败: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        etf_names = fetch_etf_names(all_codes)

        # 策略1回测
        s1_history = {c: all_history[c] for c in s1_codes}
        s1_result = _run_strategy(s1_type, s1_history, start_date, end_date, s1_capital, s1_params)
        if isinstance(s1_result, Response):
            return s1_result

        # 策略2回测
        s2_history = {c: all_history[c] for c in s2_codes}
        s2_result = _run_strategy(s2_type, s2_history, start_date, end_date, s2_capital, s2_params)
        if isinstance(s2_result, Response):
            return s2_result

        # 组合净值曲线
        combo_curve = _combine_equity_curves(
            s1_result['equity_curve'], s2_result['equity_curve']
        )

        # 组合交易记录
        s1_label = '动量' if s1_type == 'momentum' else '均值回归'
        s2_label = '动量' if s2_type == 'momentum' else '均值回归'
        combo_trades = []
        for t in s1_result.get('trade_records', []):
            rec = dict(t)
            rec['strategy'] = s1_label
            combo_trades.append(rec)
        for t in s2_result.get('trade_records', []):
            rec = dict(t)
            rec['strategy'] = s2_label
            combo_trades.append(rec)
        # 按卖出日期排序
        combo_trades.sort(key=lambda x: x.get('sellDate', ''))

        # 组合汇总
        combo_summary = build_summary(combo_curve, combo_trades, initial_capital, extra={
            "start_date": start_date,
            "end_date": end_date,
            "s1_type": s1_type,
            "s2_type": s2_type,
            "s1_weight": s1_weight,
            "s2_weight": round(s2_weight, 2),
        })

        # 子策略汇总
        s1_summary = s1_result.get('summary', {})
        s2_summary = s2_result.get('summary', {})

        return Response({
            "code": 0,
            "message": "success",
            "data": {
                "combo_equity_curve": combo_curve,
                "s1_equity_curve": s1_result['equity_curve'],
                "s2_equity_curve": s2_result['equity_curve'],
                "combo_summary": combo_summary,
                "s1_summary": s1_summary,
                "s2_summary": s2_summary,
                "trade_records": combo_trades,
                "s1_current_holding": s1_result.get('current_holding'),
                "s2_current_holding": s2_result.get('current_holding'),
                "etf_names": etf_names,
                "s1_type": s1_type,
                "s2_type": s2_type,
                "s1_label": s1_label,
                "s2_label": s2_label,
                "s1_weight": s1_weight,
                "s2_weight": round(s2_weight, 2),
            }
        })

    except Exception as e:
        return Response({
            "code": 500,
            "message": f"组合回测失败: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _run_strategy(strategy_type, etf_history_dict, start_date, end_date,
                  capital, params):
    """根据策略类型执行回测。"""
    if strategy_type == 'momentum':
        return run_rotation_backtest(
            etf_history_dict=etf_history_dict,
            start_date=start_date,
            end_date=end_date,
            initial_capital=capital,
            lookback_n=int(params.get('lookback_n', 25)),
            rebalance_days=int(params.get('rebalance_days', 5)),
        )
    elif strategy_type == 'meanrev':
        signal_type = params.get('signal_type', 'bollinger')
        return run_meanrev_backtest(
            etf_history_dict=etf_history_dict,
            start_date=start_date,
            end_date=end_date,
            initial_capital=capital,
            signal_type=signal_type,
            period=int(params.get('period', 20)),
            num_std=float(params.get('num_std', 2.0)),
            stop_loss=float(params.get('stop_loss', 0.05)),
            rebalance_days=int(params.get('rebalance_days', 1)),
            oversold=int(params.get('oversold', 30)),
            overbought=int(params.get('overbought', 70)),
        )
    else:
        return Response({"code": 400, "message": f"未知策略类型: {strategy_type}"},
                        status=status.HTTP_400_BAD_REQUEST)


def _combine_equity_curves(curve1, curve2):
    """合并两条净值曲线（按日期对齐后求和）。"""
    eq1 = {d: v for d, v in curve1}
    eq2 = {d: v for d, v in curve2}

    all_dates = sorted(set(eq1.keys()) | set(eq2.keys()))
    if not all_dates:
        return []

    # 对缺失日期用最近已知值填充
    last_v1 = curve1[0][1] if curve1 else 0
    last_v2 = curve2[0][1] if curve2 else 0

    combined = []
    for d in all_dates:
        if d in eq1:
            last_v1 = eq1[d]
        if d in eq2:
            last_v2 = eq2[d]
        combined.append((d, round(last_v1 + last_v2, 2)))

    return combined

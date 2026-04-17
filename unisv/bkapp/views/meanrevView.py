from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

import numpy as np

from ..logic.meanrev.meanrev_backtest import run_meanrev_backtest
from ..logic.common.data_fetcher import (
    fetch_etf_history, fetch_etf_names, validate_date_range,
)
from ..models.meanrev_watch import MeanrevWatch
from ..utils.usage import (
    check_and_inc_backtest, require_vip,
    QuotaExceeded, VipRequired, VIP_INFO,
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def meanrev_backtest(request):
    """均值回归回测接口。

    Query params:
        codes: ETF代码列表，逗号分隔
        start_date, end_date: 回测区间
        signal_type: 'bollinger' 或 'rsi'
        period: 指标周期，默认20
        num_std: 布林带标准差倍数，默认2.0
        oversold: RSI超卖阈值，默认30
        overbought: RSI超买阈值，默认70
        stop_loss: 止损比例，默认0.05
        rebalance_days: 调仓周期，默认1
        initial_capital: 初始资金，默认1000000
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
        codes_str = request.query_params.get('codes', '518880,513100,510300,159915')
        start_date = request.query_params.get('start_date', '2024/01/01')
        end_date = request.query_params.get('end_date', dt.today().strftime('%Y/%m/%d'))
        signal_type = request.query_params.get('signal_type', 'bollinger')
        period = int(request.query_params.get('period', 20))
        num_std = float(request.query_params.get('num_std', 2.0))
        oversold = int(request.query_params.get('oversold', 30))
        overbought = int(request.query_params.get('overbought', 70))
        stop_loss = float(request.query_params.get('stop_loss', 0.05))
        rebalance_days = int(request.query_params.get('rebalance_days', 1))
        initial_capital = float(request.query_params.get('initial_capital', 1000000))

        if signal_type not in ('bollinger', 'rsi'):
            return Response({"code": 400, "message": "signal_type 需为 'bollinger' 或 'rsi'"},
                            status=status.HTTP_400_BAD_REQUEST)
        min_period = 2 if signal_type == 'rsi' else 5
        if period < min_period or period > 120:
            return Response({"code": 400, "message": f"period 需在 {min_period}-120 之间"},
                            status=status.HTTP_400_BAD_REQUEST)

        etf_codes = [c.strip() for c in codes_str.split(',') if c.strip()]
        if len(etf_codes) < 2:
            return Response({"code": 400, "message": "至少需要2个ETF标的"},
                            status=status.HTTP_400_BAD_REQUEST)

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

        ok, err = validate_date_range(etf_history_dict, start_date, end_date)
        if not ok:
            return Response({"code": 400, "message": err},
                            status=status.HTTP_400_BAD_REQUEST)

        etf_names = fetch_etf_names(etf_codes)

        result = run_meanrev_backtest(
            etf_history_dict=etf_history_dict,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            signal_type=signal_type,
            period=period,
            num_std=num_std,
            stop_loss=stop_loss,
            rebalance_days=rebalance_days,
            oversold=oversold,
            overbought=overbought,
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
def meanrev_optimize(request):
    """均值回归参数优化：遍历 period × rebalance_days 组合。

    Query params:
        codes: ETF代码列表
        start_date, end_date: 回测区间
        signal_type: 信号类型
        initial_capital: 初始资金
        num_std: 布林带标准差倍数（固定值）
        oversold: RSI超卖阈值（固定值）
        overbought: RSI超买阈值（固定值）
        stop_loss: 止损比例（固定值）
        period_list: 周期列表，默认 '10,12,14,16,18,20,22,24,26,28,30'
        r_list: 调仓周期列表，默认 '1,2,3,4,5,6,7,8,9,10'
        oos, oos_split: 样本外验证
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
        codes_str = request.query_params.get('codes', '518880,513100,510300,159915')
        start_date = request.query_params.get('start_date', '2024/01/01')
        end_date = request.query_params.get('end_date', dt.today().strftime('%Y/%m/%d'))
        signal_type = request.query_params.get('signal_type', 'bollinger')
        initial_capital = float(request.query_params.get('initial_capital', 1000000))
        num_std = float(request.query_params.get('num_std', 2.0))
        oversold = int(request.query_params.get('oversold', 30))
        overbought = int(request.query_params.get('overbought', 70))
        stop_loss = float(request.query_params.get('stop_loss', 0.05))

        period_list_str = request.query_params.get('period_list', '10,12,14,16,18,20,22,24,26,28,30')
        r_list_str = request.query_params.get('r_list', '1,2,3,4,5,6,7,8,9,10')

        period_list = [int(x.strip()) for x in period_list_str.split(',') if x.strip()]
        r_list = [int(x.strip()) for x in r_list_str.split(',') if x.strip()]

        etf_codes = [c.strip() for c in codes_str.split(',') if c.strip()]
        if len(etf_codes) < 2:
            return Response({"code": 400, "message": "至少需要2个ETF标的"},
                            status=status.HTTP_400_BAD_REQUEST)

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

        ok, err = validate_date_range(etf_history_dict, start_date, end_date)
        if not ok:
            return Response({"code": 400, "message": err},
                            status=status.HTTP_400_BAD_REQUEST)

        oos_enabled = request.query_params.get('oos', '0') in ('1', 'true', 'True')
        oos_split = float(request.query_params.get('oos_split', 0.7))
        oos_split = max(0.5, min(0.9, oos_split))

        is_end_date = end_date
        oos_start_date = None
        if oos_enabled:
            is_end_date, oos_start_date = _split_date_range(
                etf_history_dict, start_date, end_date, oos_split
            )

        # 网格搜索：period × rebalance_days
        results = _run_meanrev_grid(
            etf_history_dict, period_list, r_list,
            start_date, is_end_date, initial_capital,
            signal_type, num_std, stop_loss,
            oversold, overbought,
            oos_enabled, oos_start_date, end_date,
        )

        _attach_smoothed_sharpe(results, period_list, r_list)
        _attach_robustness_flag(results, period_list, r_list)
        _attach_composite_score(results)

        best_sharpe = max(results, key=lambda x: x['sharpe_ratio']) if results else None
        best_robust = max(results, key=lambda x: x['smoothed_sharpe']) if results else None
        best_composite = max(results, key=lambda x: x['composite_score']) if results else None
        best_oos = None
        if oos_enabled and results:
            with_oos = [r for r in results if r.get('oos_sharpe') is not None]
            if with_oos:
                best_oos = max(with_oos, key=lambda x: x['oos_sharpe'])

        return Response({
            "code": 0,
            "message": "success",
            "data": {
                "results": results,
                "best": best_sharpe,
                "best_sharpe": best_sharpe,
                "best_robust": best_robust,
                "best_composite": best_composite,
                "best_oos": best_oos,
                "period_list": period_list,
                "r_list": r_list,
                "oos_enabled": oos_enabled,
                "oos_split": oos_split,
                "is_end_date": is_end_date,
                "oos_start_date": oos_start_date,
            }
        })

    except Exception as e:
        return Response({"code": 500, "message": f"参数优化失败: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _split_date_range(etf_history_dict, start_date, end_date, split_ratio):
    """按 split_ratio 切分样本内/外。"""
    date_sets = [set(row[0] for row in rows) for rows in etf_history_dict.values()]
    common = sorted(set.intersection(*date_sets))
    in_range = [d for d in common if start_date <= d <= end_date]
    if len(in_range) < 20:
        return end_date, None
    split_idx = int(len(in_range) * split_ratio)
    is_end = in_range[split_idx - 1]
    oos_start = in_range[split_idx]
    return is_end, oos_start


def _run_meanrev_grid(etf_history_dict, period_list, r_list,
                      start_date, is_end_date, initial_capital,
                      signal_type, num_std, stop_loss,
                      oversold, overbought,
                      oos_enabled, oos_start_date, full_end_date):
    """在 (period, rebalance_days) 网格上跑回测。"""
    results = []
    for period in period_list:
        for r in r_list:
            res = run_meanrev_backtest(
                etf_history_dict=etf_history_dict,
                start_date=start_date,
                end_date=is_end_date,
                initial_capital=initial_capital,
                signal_type=signal_type,
                period=period,
                num_std=num_std,
                stop_loss=stop_loss,
                rebalance_days=r,
                oversold=oversold,
                overbought=overbought,
            )
            s = res.get('summary', {}) or {}
            row = {
                "period": period,
                "rebalance_days": r,
                "total_return": s.get('total_return', 0),
                "annualized_return": s.get('annualized_return', 0),
                "sharpe_ratio": s.get('sharpe_ratio', 0),
                "max_drawdown": s.get('max_drawdown', 0),
                "calmar_ratio": s.get('calmar_ratio', 0),
                "win_rate": s.get('win_rate', 0),
                "total_trades": s.get('total_trades', 0),
                "final_equity": s.get('final_equity', 0),
                "is_equity_curve": res.get('equity_curve', []),
                "oos_sharpe": None,
                "oos_total_return": None,
                "oos_max_drawdown": None,
                "oos_equity_curve": None,
            }
            if oos_enabled and oos_start_date:
                oos_res = run_meanrev_backtest(
                    etf_history_dict=etf_history_dict,
                    start_date=oos_start_date,
                    end_date=full_end_date,
                    initial_capital=initial_capital,
                    signal_type=signal_type,
                    period=period,
                    num_std=num_std,
                    stop_loss=stop_loss,
                    rebalance_days=r,
                    oversold=oversold,
                    overbought=overbought,
                )
                oos_s = oos_res.get('summary', {}) or {}
                row['oos_sharpe'] = oos_s.get('sharpe_ratio', 0)
                row['oos_total_return'] = oos_s.get('total_return', 0)
                row['oos_max_drawdown'] = oos_s.get('max_drawdown', 0)
                row['oos_equity_curve'] = oos_res.get('equity_curve', [])
            results.append(row)
    return results


def _attach_smoothed_sharpe(results, period_list, r_list):
    """邻域平滑 sharpe。"""
    grid = {(r['period'], r['rebalance_days']): r['sharpe_ratio'] for r in results}
    for row in results:
        p = row['period']
        r = row['rebalance_days']
        p_idx = period_list.index(p)
        r_idx = r_list.index(r)
        neighbors = []
        for dp in (-1, 0, 1):
            for dr in (-1, 0, 1):
                pi = p_idx + dp
                ri = r_idx + dr
                if 0 <= pi < len(period_list) and 0 <= ri < len(r_list):
                    pp = period_list[pi]
                    rr = r_list[ri]
                    if (pp, rr) in grid:
                        neighbors.append(grid[(pp, rr)])
        if neighbors:
            row['smoothed_sharpe'] = round(sum(neighbors) / len(neighbors), 4)
        else:
            row['smoothed_sharpe'] = row['sharpe_ratio']


def _attach_robustness_flag(results, period_list, r_list):
    """邻居稳健性标记。"""
    grid = {(row['period'], row['rebalance_days']): row['sharpe_ratio'] for row in results}
    all_sharpes = [row['sharpe_ratio'] for row in results]
    if not all_sharpes:
        return
    overall_std = float(np.std(all_sharpes)) if len(all_sharpes) > 1 else 0.0
    threshold = max(overall_std * 0.5, 0.3)

    for row in results:
        p = row['period']
        r = row['rebalance_days']
        p_idx = period_list.index(p)
        r_idx = r_list.index(r)
        neighbors = []
        for dp in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dp == 0 and dr == 0:
                    continue
                pi = p_idx + dp
                ri = r_idx + dr
                if 0 <= pi < len(period_list) and 0 <= ri < len(r_list):
                    pp = period_list[pi]
                    rr = r_list[ri]
                    if (pp, rr) in grid:
                        neighbors.append(grid[(pp, rr)])
        if len(neighbors) >= 2:
            std_val = float(np.std(neighbors))
            row['neighbor_std'] = round(std_val, 4)
            row['robust'] = std_val <= threshold
        else:
            row['neighbor_std'] = 0.0
            row['robust'] = True


def _attach_composite_score(results):
    """综合评分。"""
    for row in results:
        sharpe = row.get('sharpe_ratio', 0) or 0
        max_dd = abs(row.get('max_drawdown', 0) or 0)
        win_rate = row.get('win_rate', 0) or 0

        score_sharpe = min(sharpe / 2.0, 1.0)
        score_dd = 1.0 - min(max_dd / 0.3, 1.0)
        score_win = max(0.0, min((win_rate - 0.4) / 0.3, 1.0))

        composite = 0.5 * score_sharpe + 0.3 * score_dd + 0.2 * score_win

        if max_dd > 0.3:
            composite *= 0.7
        if sharpe < 0.8:
            composite *= 0.8

        row['composite_score'] = round(composite, 4)


MAX_MEANREV_SUBSCRIPTIONS = 5


def _validate_meanrev_payload(payload):
    """校验均值回归订阅参数，返回 (data_dict, error_response)"""
    etf_codes = payload.get('etf_codes') or []
    if isinstance(etf_codes, str):
        etf_codes = [c.strip() for c in etf_codes.split(',') if c.strip()]
    if len(etf_codes) < 2:
        return None, Response({"code": 400, "message": "至少需要2个ETF标的"},
                              status=status.HTTP_400_BAD_REQUEST)

    try:
        signal_type = payload.get('signal_type', 'bollinger')
        period = int(payload.get('period', 20))
        num_std = float(payload.get('num_std', 2.0))
        oversold = int(payload.get('oversold', 30))
        overbought = int(payload.get('overbought', 70))
        stop_loss = float(payload.get('stop_loss', 0.05))
        rebalance_days = int(payload.get('rebalance_days', 1))
        initial_capital = float(payload.get('initial_capital', 1000000))
    except (TypeError, ValueError):
        return None, Response({"code": 400, "message": "参数格式错误"},
                              status=status.HTTP_400_BAD_REQUEST)

    if signal_type not in ('bollinger', 'rsi'):
        return None, Response({"code": 400, "message": "signal_type 需为 'bollinger' 或 'rsi'"},
                              status=status.HTTP_400_BAD_REQUEST)

    min_period = 2 if signal_type == 'rsi' else 5
    if period < min_period or period > 120:
        return None, Response({"code": 400, "message": f"period 需在 {min_period}-120 之间"},
                              status=status.HTTP_400_BAD_REQUEST)

    return {
        'etf_codes': etf_codes,
        'signal_type': signal_type,
        'period': period,
        'num_std': num_std,
        'oversold': oversold,
        'overbought': overbought,
        'stop_loss': stop_loss,
        'rebalance_days': rebalance_days,
        'initial_capital': initial_capital,
    }, None


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def meanrev_subscriptions(request):
    """均值回归订阅集合接口。

    GET  返回当前用户全部订阅
    POST body: {name, etf_codes, signal_type, period, ...} 创建（最多 5 条，VIP only）
    """
    user = request.user

    if request.method == 'GET':
        watches = MeanrevWatch.objects.filter(user=user).order_by('id')
        return Response({
            "code": 0,
            "data": [w.to_dict() for w in watches],
        })

    try:
        require_vip(user)
    except VipRequired as ve:
        return Response({
            "code": 4002,
            "message": str(ve),
            "vip_info": VIP_INFO,
        }, status=status.HTTP_403_FORBIDDEN)

    if MeanrevWatch.objects.filter(user=user).count() >= MAX_MEANREV_SUBSCRIPTIONS:
        return Response({
            "code": 400,
            "message": f"均值回归订阅最多 {MAX_MEANREV_SUBSCRIPTIONS} 条",
        }, status=status.HTTP_400_BAD_REQUEST)

    payload = request.data or {}
    data, err = _validate_meanrev_payload(payload)
    if err:
        return err

    name = (payload.get('name') or '').strip() or '未命名订阅'
    watch = MeanrevWatch.objects.create(
        user=user,
        name=name,
        enabled=True,
        **data,
    )
    return Response({
        "code": 0,
        "message": "订阅成功",
        "data": watch.to_dict(),
    })


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def meanrev_subscription_detail(request, pk):
    """单条均值回归订阅。"""
    user = request.user
    watch = MeanrevWatch.objects.filter(user=user, pk=pk).first()
    if not watch:
        return Response({"code": 404, "message": "订阅不存在"},
                        status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response({"code": 0, "data": watch.to_dict()})

    if request.method == 'DELETE':
        watch.delete()
        return Response({"code": 0, "message": "已删除"})

    payload = request.data or {}
    data, err = _validate_meanrev_payload(payload)
    if err:
        return err
    for k, v in data.items():
        setattr(watch, k, v)
    watch.save()
    return Response({"code": 0, "message": "已保存", "data": watch.to_dict()})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def meanrev_subscription_notify(request, pk):
    """切换通知开关。body: {enabled: bool}"""
    user = request.user
    watch = MeanrevWatch.objects.filter(user=user, pk=pk).first()
    if not watch:
        return Response({"code": 404, "message": "订阅不存在"},
                        status=status.HTTP_404_NOT_FOUND)
    enabled = bool((request.data or {}).get('enabled', True))
    watch.enabled = enabled
    watch.save(update_fields=['enabled', 'updated_at'])
    return Response({"code": 0, "data": watch.to_dict()})

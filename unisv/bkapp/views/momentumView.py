from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

import numpy as np

from ..logic.momentum.rotation_backtest import run_rotation_backtest
from ..logic.common.data_fetcher import (
    fetch_etf_history, fetch_etf_names, fetch_multi_etf_history,
    validate_date_range, get_market_prefix,
)
from ..models.momentum_watch import MomentumWatch
from ..utils.usage import (
    check_and_inc_backtest, require_vip,
    QuotaExceeded, VipRequired, VIP_INFO,
)




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

        # Top-N 仓位权重，如 '0.5,0.3,0.2'，默认 '1' 表示单仓全仓
        weights_str = request.query_params.get('position_weights', '1')
        try:
            position_weights = [float(x.strip()) for x in weights_str.split(',') if x.strip()]
        except ValueError:
            return Response({"code": 400, "message": "position_weights 格式错误"},
                            status=status.HTTP_400_BAD_REQUEST)
        if not position_weights:
            position_weights = [1.0]

        # 参数校验
        if lookback_n < 1 or lookback_n > 60:
            return Response({"code": 400, "message": "lookback_n 需在 1-60 之间"},
                            status=status.HTTP_400_BAD_REQUEST)

        if any(w <= 0 for w in position_weights):
            return Response({"code": 400, "message": "每个仓位权重需大于 0"},
                            status=status.HTTP_400_BAD_REQUEST)
        if sum(position_weights) > 1.0 + 1e-6:
            return Response({"code": 400, "message": "仓位权重之和不能超过 1"},
                            status=status.HTTP_400_BAD_REQUEST)
        if len(position_weights) > 10:
            return Response({"code": 400, "message": "持仓数量不能超过 10"},
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

        # 校验回测期是否落在所有 ETF 的可用数据范围内
        ok, err = validate_date_range(etf_history_dict, start_date, end_date)
        if not ok:
            return Response({"code": 400, "message": err},
                            status=status.HTTP_400_BAD_REQUEST)

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
            position_weights=position_weights,
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

        # 校验回测期是否落在所有 ETF 的可用数据范围内
        ok, err = validate_date_range(etf_history_dict, start_date, end_date)
        if not ok:
            return Response({"code": 400, "message": err},
                            status=status.HTTP_400_BAD_REQUEST)

        # 是否启用样本外验证
        oos_enabled = request.query_params.get('oos', '0') in ('1', 'true', 'True')
        oos_split = float(request.query_params.get('oos_split', 0.7))
        oos_split = max(0.5, min(0.9, oos_split))

        # 计算样本内/样本外日期切分
        is_end_date = end_date
        oos_start_date = None
        if oos_enabled:
            is_end_date, oos_start_date = _split_date_range(
                etf_history_dict, start_date, end_date, oos_split
            )

        # 遍历参数组合，每组跑 1 次或 2 次回测
        results = _run_grid(
            etf_history_dict, n_list, r_list,
            start_date, is_end_date, initial_capital,
            oos_enabled, oos_start_date, end_date,
        )

        # 计算邻域平滑 sharpe（防过拟合）
        _attach_smoothed_sharpe(results, n_list, r_list)

        # 标记每行的稳健性（邻居 sharpe 标准差是否小）
        _attach_robustness_flag(results, n_list, r_list)
        _attach_composite_score(results)

        # 各维度 best
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
                "best": best_sharpe,            # 兼容旧字段
                "best_sharpe": best_sharpe,
                "best_robust": best_robust,
                "best_composite": best_composite,
                "best_oos": best_oos,
                "n_list": n_list,
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
    """按 split_ratio 把 [start_date, end_date] 切成样本内 / 样本外两段。

    返回 (is_end_date, oos_start_date)，都是 'YYYY/MM/DD' 字符串。
    切分点选自 ETF 共同交易日，确保切点是真实交易日。
    """
    # 取 ETF 共同交易日
    date_sets = [set(row[0] for row in rows) for rows in etf_history_dict.values()]
    common = sorted(set.intersection(*date_sets))
    in_range = [d for d in common if start_date <= d <= end_date]
    if len(in_range) < 20:
        # 数据太少不切分
        return end_date, None
    split_idx = int(len(in_range) * split_ratio)
    is_end = in_range[split_idx - 1]
    oos_start = in_range[split_idx]
    return is_end, oos_start


def _run_grid(etf_history_dict, n_list, r_list,
              start_date, is_end_date, initial_capital,
              oos_enabled, oos_start_date, full_end_date):
    """在 (n, r) 参数网格上跑回测，返回 results 列表。"""
    results = []
    for n in n_list:
        for r in r_list:
            res = run_rotation_backtest(
                etf_history_dict=etf_history_dict,
                start_date=start_date,
                end_date=is_end_date,
                initial_capital=initial_capital,
                lookback_n=n,
                rebalance_days=r,
            )
            s = res.get('summary', {}) or {}
            row = {
                "lookback_n": n,
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
                oos_res = run_rotation_backtest(
                    etf_history_dict=etf_history_dict,
                    start_date=oos_start_date,
                    end_date=full_end_date,
                    initial_capital=initial_capital,
                    lookback_n=n,
                    rebalance_days=r,
                )
                oos_s = oos_res.get('summary', {}) or {}
                row['oos_sharpe'] = oos_s.get('sharpe_ratio', 0)
                row['oos_total_return'] = oos_s.get('total_return', 0)
                row['oos_max_drawdown'] = oos_s.get('max_drawdown', 0)
                row['oos_equity_curve'] = oos_res.get('equity_curve', [])
            results.append(row)
    return results


def _attach_smoothed_sharpe(results, n_list, r_list):
    """对每个 (n, r) 计算 3x3 邻域 sharpe 均值，写入 row['smoothed_sharpe']。"""
    grid = {(r['lookback_n'], r['rebalance_days']): r['sharpe_ratio'] for r in results}
    n_set = set(n_list)
    r_set = set(r_list)
    for row in results:
        n = row['lookback_n']
        r = row['rebalance_days']
        n_idx = n_list.index(n)
        r_idx = r_list.index(r)
        neighbors = []
        for dn in (-1, 0, 1):
            for dr in (-1, 0, 1):
                ni = n_idx + dn
                ri = r_idx + dr
                if 0 <= ni < len(n_list) and 0 <= ri < len(r_list):
                    nn = n_list[ni]
                    rr = r_list[ri]
                    if (nn, rr) in grid:
                        neighbors.append(grid[(nn, rr)])
        if neighbors:
            row['smoothed_sharpe'] = round(sum(neighbors) / len(neighbors), 4)
        else:
            row['smoothed_sharpe'] = row['sharpe_ratio']


def _attach_robustness_flag(results, n_list, r_list):
    """对每个 (n, r) 计算邻居 sharpe 的标准差，标记是否过拟合。

    robust=True   邻居一致（std 小）
    robust=False  邻居波动大（std 大），有过拟合嫌疑
    """
    grid = {(row['lookback_n'], row['rebalance_days']): row['sharpe_ratio'] for row in results}
    # 用全网格 sharpe 的中位差作为阈值
    all_sharpes = [row['sharpe_ratio'] for row in results]
    if not all_sharpes:
        return
    overall_std = float(np.std(all_sharpes)) if len(all_sharpes) > 1 else 0.0
    threshold = max(overall_std * 0.5, 0.3)  # 邻居 std 超过这个就算"波动大"

    for row in results:
        n = row['lookback_n']
        r = row['rebalance_days']
        n_idx = n_list.index(n)
        r_idx = r_list.index(r)
        neighbors = []
        for dn in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dn == 0 and dr == 0:
                    continue
                ni = n_idx + dn
                ri = r_idx + dr
                if 0 <= ni < len(n_list) and 0 <= ri < len(r_list):
                    nn = n_list[ni]
                    rr = r_list[ri]
                    if (nn, rr) in grid:
                        neighbors.append(grid[(nn, rr)])
        if len(neighbors) >= 2:
            std = float(np.std(neighbors))
            row['neighbor_std'] = round(std, 4)
            row['robust'] = std <= threshold
        else:
            row['neighbor_std'] = 0.0
            row['robust'] = True


def _attach_composite_score(results):
    """综合评分：标准化 + 加权 + 惩罚。

    标准化（压到 0~1）：
      夏普得分  = min(sharpe / 2.0, 1.0)
      回撤得分  = 1 - min(|max_dd| / 0.3, 1.0)
      胜率得分  = clamp((win_rate - 0.4) / 0.3, 0, 1)

    加权：0.5 × 夏普 + 0.3 × 回撤 + 0.2 × 胜率

    惩罚：
      |max_dd| > 0.3 → ×0.7
      sharpe < 0.8   → ×0.8
    """
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


MAX_MOMENTUM_SUBSCRIPTIONS = 5


def _validate_momentum_payload(payload):
    """校验动量订阅参数，返回 (data_dict, error_response)"""
    etf_codes = payload.get('etf_codes') or []
    if isinstance(etf_codes, str):
        etf_codes = [c.strip() for c in etf_codes.split(',') if c.strip()]
    if len(etf_codes) < 2:
        return None, Response({"code": 400, "message": "至少需要2个ETF标的"},
                              status=status.HTTP_400_BAD_REQUEST)

    try:
        lookback_n = int(payload.get('lookback_n', 25))
        rebalance_days = int(payload.get('rebalance_days', 5))
        initial_capital = float(payload.get('initial_capital', 1000000))
    except (TypeError, ValueError):
        return None, Response({"code": 400, "message": "参数格式错误"},
                              status=status.HTTP_400_BAD_REQUEST)

    if lookback_n < 1 or lookback_n > 60:
        return None, Response({"code": 400, "message": "lookback_n 需在 1-60 之间"},
                              status=status.HTTP_400_BAD_REQUEST)

    return {
        'etf_codes': etf_codes,
        'lookback_n': lookback_n,
        'rebalance_days': rebalance_days,
        'initial_capital': initial_capital,
    }, None


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def momentum_subscriptions(request):
    """动量轮动订阅集合接口。

    GET  返回当前用户全部订阅 [{...}]
    POST body: {name, etf_codes, lookback_n, rebalance_days, initial_capital}
         创建一条新订阅（每个用户最多 5 条，VIP only）
    """
    user = request.user

    if request.method == 'GET':
        watches = MomentumWatch.objects.filter(user=user).order_by('id')
        return Response({
            "code": 0,
            "data": [w.to_dict() for w in watches],
        })

    # POST: 创建
    try:
        require_vip(user)
    except VipRequired as ve:
        return Response({
            "code": 4002,
            "message": str(ve),
            "vip_info": VIP_INFO,
        }, status=status.HTTP_403_FORBIDDEN)

    if MomentumWatch.objects.filter(user=user).count() >= MAX_MOMENTUM_SUBSCRIPTIONS:
        return Response({
            "code": 400,
            "message": f"动量轮动订阅最多 {MAX_MOMENTUM_SUBSCRIPTIONS} 条",
        }, status=status.HTTP_400_BAD_REQUEST)

    payload = request.data or {}
    data, err = _validate_momentum_payload(payload)
    if err:
        return err

    name = (payload.get('name') or '').strip() or '未命名订阅'
    watch = MomentumWatch.objects.create(
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
def momentum_subscription_detail(request, pk):
    """单条动量订阅。

    GET    返回该订阅
    PUT    更新参数（不修改 name）
    DELETE 删除
    """
    user = request.user
    watch = MomentumWatch.objects.filter(user=user, pk=pk).first()
    if not watch:
        return Response({"code": 404, "message": "订阅不存在"},
                        status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response({"code": 0, "data": watch.to_dict()})

    if request.method == 'DELETE':
        watch.delete()
        return Response({"code": 0, "message": "已删除"})

    # PUT
    payload = request.data or {}
    data, err = _validate_momentum_payload(payload)
    if err:
        return err
    for k, v in data.items():
        setattr(watch, k, v)
    watch.save()
    return Response({"code": 0, "message": "已保存", "data": watch.to_dict()})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def momentum_subscription_notify(request, pk):
    """切换通知开关。body: {enabled: bool}"""
    user = request.user
    watch = MomentumWatch.objects.filter(user=user, pk=pk).first()
    if not watch:
        return Response({"code": 404, "message": "订阅不存在"},
                        status=status.HTTP_404_NOT_FOUND)
    enabled = bool((request.data or {}).get('enabled', True))
    watch.enabled = enabled
    watch.save(update_fields=['enabled', 'updated_at'])
    return Response({"code": 0, "data": watch.to_dict()})


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

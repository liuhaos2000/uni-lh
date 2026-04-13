"""动量轮动决策函数。

将"今日是否调仓、买卖什么"的纯逻辑独立出来，
让回测和实盘信号推送共享同一份判断规则。

双动量策略（Dual Momentum）：
  - 相对动量：在 ETF 池中选评分最高的标的
  - 绝对动量：最高评分必须 > abs_threshold 才允许持仓，否则空仓
"""

# 绝对动量阈值：评分低于此值时空仓，避免在震荡/下跌市频繁交易
# 无风险年化 2.5%，换算到约 25 个交易日的对数收益率 ≈ 0.025/242*25 ≈ 0.0026
# 除以典型日波动率 ~0.01 得到约 0.26，取 0.2 留一点容差
ABS_MOMENTUM_THRESHOLD = 0.2


def decide_signal(scores, holding_code, days_since_rebalance, rebalance_days,
                   above_ma=None, abs_threshold=ABS_MOMENTUM_THRESHOLD):
    """根据当日动量评分给出操作建议。

    Args:
        scores: dict, {etf_code: score or None}
        holding_code: str or None, 当前持仓 ETF 代码 (None 表示空仓)
        days_since_rebalance: int, 距离上次调仓的天数（含今日）
        rebalance_days: int, 调仓周期（交易日）
        above_ma: dict or None, 均线过滤（保留兼容，默认不启用）
        abs_threshold: float, 绝对动量阈值，最高评分低于此值时空仓

    Returns:
        dict: {
            'action': 'hold' | 'sell' | 'buy' | 'swap',
            'target_code': str or None,
            'reason': str,
            'is_rebalance_day': bool,
        }
    """
    is_rebalance_day = days_since_rebalance >= rebalance_days

    # 未到调仓日，无条件持有
    if not is_rebalance_day:
        return {
            'action': 'hold',
            'target_code': holding_code,
            'reason': '未到调仓日',
            'is_rebalance_day': False,
        }

    # 数据不足（评分为空），不动作
    if not scores:
        return {
            'action': 'hold',
            'target_code': holding_code,
            'reason': '评分数据不足',
            'is_rebalance_day': False,
        }

    # 如果启用了均线过滤，把均线之下的标的评分视为负分
    filtered_scores = dict(scores)
    if above_ma is not None:
        for code, s in filtered_scores.items():
            if s is not None and not above_ma.get(code, True):
                filtered_scores[code] = -abs(s) if s > 0 else s

    # 找最高分
    best_code = max(
        filtered_scores,
        key=lambda c: filtered_scores[c] if filtered_scores[c] is not None else float('-inf'),
    )
    best_score = filtered_scores.get(best_code)

    # 双动量 — 绝对动量判断：最高分低于阈值则空仓
    if best_score is None or best_score < abs_threshold:
        if holding_code:
            return {
                'action': 'sell',
                'target_code': None,
                'reason': f'绝对动量不足(最高{best_score:.2f}<{abs_threshold})空仓',
                'is_rebalance_day': True,
            }
        return {
            'action': 'hold',
            'target_code': None,
            'reason': f'绝对动量不足继续空仓',
            'is_rebalance_day': True,
        }

    # 相对动量 — 最高分仍是当前持仓，继续持有
    if best_code == holding_code:
        return {
            'action': 'hold',
            'target_code': holding_code,
            'reason': '最高分仍是当前持仓',
            'is_rebalance_day': True,
        }

    if holding_code:
        return {
            'action': 'swap',
            'target_code': best_code,
            'reason': '调仓换股',
            'is_rebalance_day': True,
        }

    return {
        'action': 'buy',
        'target_code': best_code,
        'reason': '建仓买入',
        'is_rebalance_day': True,
    }

"""动量轮动决策函数。

将"今日是否调仓、买卖什么"的纯逻辑独立出来，
让回测和实盘信号推送共享同一份判断规则。
"""


def decide_signal(scores, holding_code, days_since_rebalance, rebalance_days):
    """根据当日动量评分给出操作建议。

    Args:
        scores: dict, {etf_code: score or None}
        holding_code: str or None, 当前持仓 ETF 代码 (None 表示空仓)
        days_since_rebalance: int, 距离上次调仓的天数（含今日）
        rebalance_days: int, 调仓周期（交易日）

    Returns:
        dict: {
            'action': 'hold' | 'sell' | 'buy' | 'swap',
            'target_code': str or None,   # 操作后的目标持仓（None 表示空仓）
            'reason': str,
            'is_rebalance_day': bool,     # 今天是否到了调仓判定日
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

    # 全部评分为负 → 空仓 / 维持空仓
    all_negative = all(
        (s is not None and s < 0) for s in scores.values()
    )
    if all_negative:
        if holding_code:
            return {
                'action': 'sell',
                'target_code': None,
                'reason': '全部负分空仓',
                'is_rebalance_day': True,
            }
        return {
            'action': 'hold',
            'target_code': None,
            'reason': '全部负分继续空仓',
            'is_rebalance_day': True,
        }

    # 找最高分
    best_code = max(
        scores,
        key=lambda c: scores[c] if scores[c] is not None else float('-inf'),
    )

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

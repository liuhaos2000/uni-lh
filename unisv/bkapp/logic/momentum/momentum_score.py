import numpy as np
from .r2 import calculate_r2


def calculate_momentum_score(prices, n=25):
    """计算动量评分 = N日涨幅 * R²系数。

    Args:
        prices: 收盘价序列（按时间顺序），长度应 >= n
        n: 回看天数，默认25

    Returns:
        float or None: 动量评分，数据不足时返回 None
    """
    if len(prices) < n:
        return None

    recent_prices = prices[-n:]

    # N日涨幅
    change_rate = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]

    # R²系数
    r2 = calculate_r2(recent_prices)

    return change_rate * r2

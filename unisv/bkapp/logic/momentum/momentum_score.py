import numpy as np


def calculate_momentum_score(prices, n=25):
    """计算动量评分 = 波动率调整动量。

    score = N日对数收益率 / N日波动率

    本质是用风险调整后的收益来排序，波动小但稳定上涨的 ETF 得分更高。

    Args:
        prices: 收盘价序列（按时间顺序），长度应 >= n
        n: 回看天数，默认25

    Returns:
        float or None: 动量评分，数据不足时返回 None
    """
    if len(prices) < n:
        return None

    recent_prices = np.array(prices[-n:], dtype=float)

    # N日对数收益率
    log_return = np.log(recent_prices[-1] / recent_prices[0])

    # 日收益率序列的标准差（波动率）
    daily_returns = np.diff(recent_prices) / recent_prices[:-1]
    vol = np.std(daily_returns)

    if vol < 1e-10:
        return log_return * 100 if log_return > 0 else 0.0

    return log_return / vol

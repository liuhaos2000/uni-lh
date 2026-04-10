import numpy as np


def calculate_r2(prices):
    """计算价格序列与完美斜线的R²拟合系数。

    R²衡量价格走势与一条完美直线的贴合程度：
    - 接近1：走势非常线性（趋势明确）
    - 接近0：走势杂乱（无明确趋势）

    Args:
        prices: 价格序列（list 或 numpy array），按时间顺序排列

    Returns:
        float: R²系数，范围 [0, 1]
    """
    prices = np.array(prices, dtype=float)
    n = len(prices)
    if n < 2:
        return 0.0

    x = np.arange(n)
    y = prices

    # 线性回归：y = a*x + b
    x_mean = x.mean()
    y_mean = y.mean()

    ss_xy = np.sum((x - x_mean) * (y - y_mean))
    ss_xx = np.sum((x - x_mean) ** 2)

    if ss_xx == 0:
        return 0.0

    slope = ss_xy / ss_xx
    intercept = y_mean - slope * x_mean

    y_pred = slope * x + intercept

    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)

    if ss_tot == 0:
        return 0.0

    r2 = 1 - ss_res / ss_tot
    return max(r2, 0.0)

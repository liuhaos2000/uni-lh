"""均值回归信号生成模块。

可插拔设计：通过 signal_type 参数切换不同的信号算法。
目前支持：
  - bollinger: 布林带信号
  - rsi: RSI 超买超卖信号（待实现）
"""
import numpy as np


def compute_signal(prices, signal_type='bollinger', **params):
    """统一的信号计算入口。

    Args:
        prices: 收盘价序列（按时间顺序），list of float
        signal_type: 信号类型，'bollinger' 或 'rsi'
        **params: 策略参数

    Returns:
        dict: {
            'action': 'buy' | 'sell' | 'hold',
            'reason': str,
            'deviation': float,  # 偏离度（标准化），越负越超卖
            'indicator': dict,   # 指标详情（如布林带上中下轨）
        }
    """
    if signal_type == 'bollinger':
        return _bollinger_signal(prices, **params)
    elif signal_type == 'rsi':
        return _rsi_signal(prices, **params)
    else:
        raise ValueError(f"未知信号类型: {signal_type}")


def compute_deviation(prices, signal_type='bollinger', **params):
    """计算偏离度，用于多标的比较谁最超卖。

    返回标准化偏离度：负值越大 = 越超卖，正值越大 = 越超买。
    """
    if signal_type == 'bollinger':
        return _bollinger_deviation(prices, **params)
    elif signal_type == 'rsi':
        return _rsi_deviation(prices, **params)
    else:
        raise ValueError(f"未知信号类型: {signal_type}")


# ==================== 布林带 ====================

def _bollinger_signal(prices, period=20, num_std=2.0, **_):
    """布林带信号。

    买入：价格跌破下轨
    卖出：价格回到中轨（均线）以上
    """
    if len(prices) < period:
        return {'action': 'hold', 'reason': '数据不足', 'deviation': 0.0, 'indicator': {}}

    recent = np.array(prices[-period:], dtype=float)
    ma = np.mean(recent)
    std = np.std(recent)

    if std < 1e-10:
        return {'action': 'hold', 'reason': '波动率为零', 'deviation': 0.0, 'indicator': {}}

    upper = ma + num_std * std
    lower = ma - num_std * std
    current = prices[-1]
    deviation = (current - ma) / std  # 标准化偏离度

    indicator = {
        'ma': round(ma, 4),
        'upper': round(upper, 4),
        'lower': round(lower, 4),
        'std': round(std, 4),
        'current': round(current, 4),
    }

    if current <= lower:
        return {'action': 'buy', 'reason': f'跌破下轨({round(lower,2)})', 'deviation': deviation, 'indicator': indicator}
    elif current >= ma:
        return {'action': 'sell', 'reason': f'回到中轨({round(ma,2)})以上', 'deviation': deviation, 'indicator': indicator}
    else:
        return {'action': 'hold', 'reason': '介于下轨与中轨之间', 'deviation': deviation, 'indicator': indicator}


def _bollinger_deviation(prices, period=20, num_std=2.0, **_):
    """布林带偏离度。"""
    if len(prices) < period:
        return 0.0
    recent = np.array(prices[-period:], dtype=float)
    ma = np.mean(recent)
    std = np.std(recent)
    if std < 1e-10:
        return 0.0
    return (prices[-1] - ma) / std


# ==================== RSI（预留扩展） ====================

def _rsi_signal(prices, period=14, oversold=30, overbought=70, **_):
    """RSI 信号。"""
    rsi = _calculate_rsi(prices, period)
    if rsi is None:
        return {'action': 'hold', 'reason': '数据不足', 'deviation': 0.0, 'indicator': {}}

    indicator = {'rsi': round(rsi, 2)}
    # RSI 转化为偏离度：50 为中性，<30 超卖，>70 超买
    deviation = (rsi - 50) / 50  # [-1, 1]

    if rsi <= oversold:
        return {'action': 'buy', 'reason': f'RSI超卖({round(rsi,1)})', 'deviation': deviation, 'indicator': indicator}
    elif rsi >= overbought:
        return {'action': 'sell', 'reason': f'RSI超买({round(rsi,1)})', 'deviation': deviation, 'indicator': indicator}
    else:
        return {'action': 'hold', 'reason': f'RSI中性({round(rsi,1)})', 'deviation': deviation, 'indicator': indicator}


def _rsi_deviation(prices, period=14, **_):
    """RSI 偏离度。"""
    rsi = _calculate_rsi(prices, period)
    if rsi is None:
        return 0.0
    return (rsi - 50) / 50


def _calculate_rsi(prices, period=14):
    """计算 RSI 值。"""
    if len(prices) < period + 1:
        return None
    prices = np.array(prices, dtype=float)
    deltas = np.diff(prices[-period - 1:])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    if avg_loss < 1e-10:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)

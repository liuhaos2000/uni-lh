"""多维条件策略 · 逐日指标计算。

四个维度（v2 设计）：
- 趋势 (trend):    close > MA(long)  AND  MA(short) > MA(long)
- 动量 (momentum): 过去 N 日累计收益 > 0
- 量价 (volprice): 量比 > 阈值  AND  N 日累计带方向资金流 > 0
- 风控 (risk):     距 lookback 日高点回撤 < 阈值（即未深度回撤）

每个维度都可以被禁用；禁用后视为恒真，但在画面上以灰色格子显示。
"""
from __future__ import annotations


# ─────────────────────────── 工具 ───────────────────────────

def _sma(values, n):
    """简单移动平均；结果与 values 等长，不足 n 的位置为 None。"""
    out = [None] * len(values)
    if n <= 0 or len(values) < n:
        return out
    s = sum(values[:n])
    out[n - 1] = s / n
    for i in range(n, len(values)):
        s += values[i] - values[i - n]
        out[i] = s / n
    return out


# ─────────────────────────── 维度计算 ───────────────────────────

def compute_trend_series(closes, short_period, long_period):
    """趋势：close > MA(long) AND MA(short) > MA(long)。

    返回 (ma_short, ma_long, flag_list)。
    """
    ma_short = _sma(closes, short_period)
    ma_long = _sma(closes, long_period)
    flags = [False] * len(closes)
    for i in range(len(closes)):
        if ma_short[i] is None or ma_long[i] is None:
            flags[i] = False
            continue
        flags[i] = (closes[i] > ma_long[i]) and (ma_short[i] > ma_long[i])
    return ma_short, ma_long, flags


def compute_momentum_series(closes, period):
    """动量：过去 period 日累计收益 > 0。

    返回 (pct_list, flag_list)。pct[i] = (close[i] - close[i-period]) / close[i-period]。
    """
    n = len(closes)
    pct = [None] * n
    flags = [False] * n
    for i in range(n):
        if i < period:
            continue
        base = closes[i - period]
        if base <= 0:
            continue
        p = (closes[i] - base) / base
        pct[i] = p
        flags[i] = p > 0
    return pct, flags


def compute_volprice_series(closes, volumes, ratio_period, flow_period, ratio_threshold=0.9):
    """量价：近期均量比 > 阈值 AND 累计带方向资金流 > 0。

    - 量比[i] = mean(volume[i-flow_period+1 .. i]) / mean(volume[i-ratio_period+1 .. i])
      （近 flow_period 日均量 / 近 ratio_period 日均量；表征"近期量能相对整体偏强"）
    - 资金流[i] = Σ_{j=i-flow_period+1..i} sign(close[j]-close[j-1]) * volume[j]
      （上涨日成交量计正、下跌日计负，作为资金净流入代理）

    flag[i] = (量比 > ratio_threshold) AND (资金流 > 0)

    返回 (ratio_list, flow_list, vol_ma_recent, vol_ma_basis, flag_list)。
    - vol_ma_recent: flow_period 日成交量均线（量比的分子）
    - vol_ma_basis : ratio_period 日成交量均线（量比的分母 / 基准）
    """
    n = len(closes)
    vol_ma_recent = _sma(volumes, flow_period)
    vol_ma_basis = _sma(volumes, ratio_period)
    ratios = [None] * n
    flows = [None] * n
    flags = [False] * n
    for i in range(n):
        if vol_ma_recent[i] is not None and vol_ma_basis[i] and vol_ma_basis[i] > 0:
            ratios[i] = vol_ma_recent[i] / vol_ma_basis[i]
        if i >= flow_period:
            f = 0.0
            for j in range(i - flow_period + 1, i + 1):
                if j == 0:
                    continue
                dc = closes[j] - closes[j - 1]
                sign = 1 if dc > 0 else (-1 if dc < 0 else 0)
                f += sign * volumes[j]
            flows[i] = f
        r = ratios[i]
        f = flows[i]
        if r is not None and f is not None:
            flags[i] = (r > ratio_threshold) and (f > 0)
    return ratios, flows, vol_ma_recent, vol_ma_basis, flags


def compute_atr(highs, lows, closes, period=14):
    """Wilder True Range 的 SMA 平均。

    TR[t] = max(high[t]-low[t], |high[t]-close[t-1]|, |low[t]-close[t-1]|)
    ATR[t] = SMA(TR, period)

    返回 atr_list（与输入等长，前 period-1 个为 None）。
    """
    n = len(closes)
    if n == 0 or period <= 0:
        return [None] * n
    tr = [0.0] * n
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
    return _sma(tr, period)


def _resolve_eff_pct(idx, mode, atr_series, closes, k, fixed_pct,
                     clamp_min=0.01, clamp_max=0.30):
    """根据模式得到第 idx 日的等效百分比阈值。

    mode='fixed'  → 直接返回 fixed_pct
    mode='atr'    → k × ATR[idx] / close[idx]，clamp 在 [min, max]，超界回退到 fixed_pct
    """
    if mode == 'atr' and idx < len(atr_series):
        atr = atr_series[idx]
        c = closes[idx] if idx < len(closes) else 0
        if atr is not None and c > 0:
            t = k * atr / c
            if clamp_min <= t <= clamp_max:
                return t
    return fixed_pct


def compute_risk_series(closes, highs, lows, lookback,
                        mode='fixed',
                        fixed_threshold=0.08,
                        atr_period=14,
                        atr_k=2.0):
    """风控：距 lookback 日高点回撤 ≤ 阈值（即"未深度回撤"才允许开仓）。

    drawdown[i] = (close[i] - max(high[i-lookback+1 .. i])) / max
    flag[i]     = drawdown[i] ≥ −threshold(i)

    mode='fixed': threshold(i) = fixed_threshold（恒定）
    mode='atr'  : threshold(i) = atr_k × ATR(i)/close(i)，异常值回退 fixed_threshold

    返回 (drawdown_list, flag_list, eff_threshold_list)。eff_threshold_list 用于统计/展示。
    """
    n = len(closes)
    dds = [None] * n
    flags = [False] * n
    eff_thresh = [None] * n
    if lookback <= 0:
        return dds, flags, eff_thresh

    if mode == 'atr':
        atr_series = compute_atr(highs, lows, closes, atr_period)
    else:
        atr_series = [None] * n

    for i in range(n):
        t = _resolve_eff_pct(i, mode, atr_series, closes, atr_k, fixed_threshold)
        eff_thresh[i] = t
        threshold = -abs(t)
        start = max(0, i - lookback + 1)
        peak = max(highs[start:i + 1]) if i + 1 > start else None
        if peak and peak > 0:
            dd = (closes[i] - peak) / peak
            dds[i] = dd
            flags[i] = dd >= threshold
    return dds, flags, eff_thresh


# ─────────────────────────── 缓冲 + 合成 ───────────────────────────

def apply_buffer(raw_flags, entry_days=2, exit_days=1):
    """给单个维度的 flag 序列加"状态缓冲"，进出场不对称。

    - False → True（进场确认）：需要连续 entry_days 天原始 True
    - True  → False（出场确认）：需要连续 exit_days 天原始 False

    设计意图：进场要求严格以抑制抖动，出场要求宽松以快速止损/控回撤。
    任一参数 <= 1 表示该方向不需要缓冲，立即翻转。
    """
    entry_days = max(1, int(entry_days))
    exit_days = max(1, int(exit_days))
    if entry_days == 1 and exit_days == 1:
        return list(raw_flags)
    state = False
    out = []
    for i, r in enumerate(raw_flags):
        if r != state:
            need = entry_days if state is False else exit_days
            start = i - need + 1
            if start < 0:
                out.append(state)
                continue
            window = raw_flags[start:i + 1]
            if all(x != state for x in window):
                state = not state
        out.append(state)
    return out


def compute_market_gate(market_closes, ma_period):
    """市场环境过滤：大盘指数收盘 > MA(ma_period) → True。

    Args:
        market_closes: 与回测日期对齐的指数收盘价列表，可含 None（该日指数无数据）。
        ma_period: 均线周期。

    Returns:
        (flags, ma_out)，与输入等长。flags[i]=False 时意味着"大盘空头，不允许新开仓"。
    """
    n = len(market_closes)
    flags = [False] * n
    ma_out = [None] * n
    if ma_period <= 0 or n == 0:
        return flags, ma_out
    window = []
    for i, c in enumerate(market_closes):
        if c is None:
            window = []
            continue
        window.append(c)
        if len(window) > ma_period:
            window.pop(0)
        if len(window) == ma_period:
            avg = sum(window) / ma_period
            ma_out[i] = avg
            flags[i] = c > avg
    return flags, ma_out


DIMENSIONS = ('trend', 'momentum', 'volprice', 'risk')


def combine_flags(series_by_dim, enabled_by_dim, min_count=None):
    """把各维度的 flag 序列按"N-of-M"模式合并。

    Args:
        series_by_dim: {dim: [bool, ...]}，所有序列长度相同。
        enabled_by_dim: {dim: bool}
        min_count:  None       → 等价于 AND（启用维度全部满足）
                    整数 N     → 启用维度里满足数量 ≥ N 即开仓
                                  （N 会被 clamp 到 [1, 启用维度数]）

    特殊情形：
        - 启用维度数为 0：返回全 True（保持旧行为：无条件等价于"无过滤"）

    Returns:
        [bool, ...] 总买持信号
    """
    length = max((len(arr) for arr in series_by_dim.values()), default=0)
    enabled_dims = [d for d in DIMENSIONS if enabled_by_dim.get(d, False)]
    if not enabled_dims:
        return [True] * length

    n_enabled = len(enabled_dims)
    if min_count is None:
        threshold = n_enabled
    else:
        threshold = max(1, min(int(min_count), n_enabled))

    out = []
    for i in range(length):
        count = 0
        for dim in enabled_dims:
            arr = series_by_dim.get(dim)
            if arr and i < len(arr) and arr[i]:
                count += 1
        out.append(count >= threshold)
    return out

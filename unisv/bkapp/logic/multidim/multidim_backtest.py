"""多维条件策略 · 单标的全仓回测（v2 维度）。

规则：
- 每个交易日 t 收盘后判断启用的 N 个维度，得到信号 S(t)
- 信号在 t+1 日收盘价执行（避免未来函数 / 同日成交不可执行）
- 空仓时若 S(t)=True，次日（t+1）以收盘价买入
- 持仓时若 S(t)=False，次日以收盘价卖出
- 计入 A 股交易成本：单边佣金 + 卖出印花税
- 单标的全仓，无止损（出场由信号驱动）

四个维度：趋势 / 动量 / 量价 / 风控（详见 signals.py）。
"""
from __future__ import annotations

from .signals import (
    compute_trend_series,
    compute_momentum_series,
    compute_volprice_series,
    compute_risk_series,
    compute_market_gate,
    compute_atr,
    _resolve_eff_pct,
    combine_flags,
    apply_buffer,
    DIMENSIONS,
)
from ..common.metrics import (
    build_summary,
    calculate_annualized_return,
    calculate_max_drawdown,
)


# 维度状态缓冲：进场严格、出场宽松
ENTRY_BUFFER_DAYS = 2
EXIT_BUFFER_DAYS = 1

# A 股交易成本
DEFAULT_COMMISSION_RATE = 0.00025  # 单边佣金 万分之 2.5
DEFAULT_STAMP_DUTY_RATE = 0.0005   # 印花税 千分之 5（仅卖出）


def run_multidim_backtest(
    stock_history,  # [[date, open, high, low, close, volume], ...]
    stock_code,
    start_date,
    end_date=None,
    initial_capital=1000000,
    # 趋势：close > MA(long)  AND  MA(short) > MA(long)
    trend_enabled=True,
    trend_short_period=20,
    trend_long_period=60,
    # 动量：过去 N 日累计收益 > 0
    momentum_enabled=True,
    momentum_period=60,
    # 量价：近期均量比 > 阈值  AND  N 日累计带方向资金流 > 0
    volprice_enabled=True,
    volprice_ratio_period=20,
    volprice_flow_period=5,
    volprice_ratio_threshold=0.9,
    # 风控：距 N 日高点回撤 < 阈值
    risk_enabled=True,
    risk_lookback=60,
    risk_drawdown_threshold=0.08,
    risk_mode='fixed',           # 'fixed' or 'atr'
    risk_atr_k=2.0,
    # 合成模式：None = 启用维度全部满足（AND）；整数 N = N-of-M（启用维度里满足 ≥N 个）
    min_match_count=None,
    # 跟踪止损：持仓期间维护"持仓后最高收盘价 H"，当 close < H × (1 - trail_pct) 时强制卖出
    trailing_stop_enabled=False,
    trail_pct=0.10,
    trail_mode='fixed',          # 'fixed' or 'atr'
    trail_atr_k=3.0,
    # ATR 周期（风控和止损共享）
    atr_period=14,
    # 市场过滤（独立 gate，仅过滤新开仓，不强制平仓）
    market_filter_enabled=False,
    market_closes=None,        # list[float|None]，与 stock_history 长度一致；None 表示该日指数无数据
    market_ma_period=60,
    # 交易成本
    commission_rate=DEFAULT_COMMISSION_RATE,
    stamp_duty_rate=DEFAULT_STAMP_DUTY_RATE,
):
    """执行多维条件策略回测。

    所有比例参数用小数（0.08 = 8%, 0.00025 = 万 2.5）。
    """
    if not stock_history:
        return _empty_result(initial_capital, stock_code)

    dates   = [row[0] for row in stock_history]
    opens   = [float(row[1]) for row in stock_history]
    highs   = [float(row[2]) for row in stock_history]
    lows    = [float(row[3]) for row in stock_history]
    closes  = [float(row[4]) for row in stock_history]
    volumes = [float(row[5]) for row in stock_history]

    # ── 指标序列（贯穿全历史）──
    trend_ma_short, trend_ma_long, trend_raw = compute_trend_series(
        closes, trend_short_period, trend_long_period
    )
    momentum_pct, momentum_raw = compute_momentum_series(closes, momentum_period)
    vol_ratios, vol_flows, vol_ma_recent, vol_ma_basis, volprice_raw = compute_volprice_series(
        closes, volumes, volprice_ratio_period, volprice_flow_period, volprice_ratio_threshold
    )
    drawdowns, risk_raw, risk_eff_thresh = compute_risk_series(
        closes, highs, lows, risk_lookback,
        mode=risk_mode,
        fixed_threshold=risk_drawdown_threshold,
        atr_period=atr_period,
        atr_k=risk_atr_k,
    )

    # ATR 序列（trailing stop 也要用，按需计算一次）
    if trail_mode == 'atr' or risk_mode == 'atr':
        atr_series = compute_atr(highs, lows, closes, atr_period)
    else:
        atr_series = [None] * len(closes)

    # 不对称缓冲（进场 2 日确认 / 出场 1 日即翻）
    trend_flags = apply_buffer(trend_raw, ENTRY_BUFFER_DAYS, EXIT_BUFFER_DAYS)
    momentum_flags = apply_buffer(momentum_raw, ENTRY_BUFFER_DAYS, EXIT_BUFFER_DAYS)
    volprice_flags = apply_buffer(volprice_raw, ENTRY_BUFFER_DAYS, EXIT_BUFFER_DAYS)
    risk_flags = apply_buffer(risk_raw, ENTRY_BUFFER_DAYS, EXIT_BUFFER_DAYS)

    enabled = {
        'trend': trend_enabled,
        'momentum': momentum_enabled,
        'volprice': volprice_enabled,
        'risk': risk_enabled,
    }
    all_flags = combine_flags(
        {
            'trend': trend_flags,
            'momentum': momentum_flags,
            'volprice': volprice_flags,
            'risk': risk_flags,
        },
        enabled,
        min_count=min_match_count,
    )

    # 市场过滤：与 dates 长度一致的 gate flags
    if market_filter_enabled and market_closes and len(market_closes) == len(dates):
        market_gate_flags, market_ma = compute_market_gate(market_closes, market_ma_period)
    else:
        market_gate_flags = [True] * len(dates)
        market_ma = [None] * len(dates)

    # ── 裁剪到回测区间 ──
    in_range_idx = [
        i for i, d in enumerate(dates)
        if d >= start_date and (end_date is None or d <= end_date)
    ]
    if not in_range_idx:
        return _empty_result(initial_capital, stock_code)

    # ── 回测主循环 ──
    capital = float(initial_capital)
    holding_shares = 0
    buy_price = 0.0
    buy_price_raw = 0.0
    buy_date = None
    # 跟踪止损：持仓后最高收盘价（只升不降，平仓时清零）
    max_close_since_entry = 0.0

    equity_curve = []
    trade_records = []

    # 用于统计"实际生效的等效幅度"
    trail_eff_during_hold = []

    for pos, idx in enumerate(in_range_idx):
        date = dates[idx]
        close = closes[idx]
        # 信号延迟一日：用上一交易日的合成信号决定本日动作
        signal = all_flags[in_range_idx[pos - 1]] if pos > 0 else False
        # 市场过滤（仅作用于新开仓）：用上一交易日的指数 gate 决定今日是否允许买入
        market_ok = market_gate_flags[in_range_idx[pos - 1]] if pos > 0 else False

        # 跟踪止损：若昨日收盘已跌破"H × (1 - eff_trail_pct)"，今日强制卖出
        # （H = max_close_since_entry，是截至昨日收盘的持仓后最高，不含今日）
        stop_triggered = False
        if (holding_shares > 0 and trailing_stop_enabled
                and pos > 0 and max_close_since_entry > 0):
            prev_idx = in_range_idx[pos - 1]
            prev_close = closes[prev_idx]
            # 用昨日的 ATR 决定昨日生效的 trail_pct（本日动作依据昨日信息）
            eff_trail = _resolve_eff_pct(prev_idx, trail_mode, atr_series, closes,
                                         trail_atr_k, trail_pct)
            stop_line = max_close_since_entry * (1 - eff_trail)
            if prev_close < stop_line:
                stop_triggered = True

        # 持仓中记录当日的等效 trail，用于回测后统计平均
        if holding_shares > 0 and trailing_stop_enabled:
            trail_eff_during_hold.append(
                _resolve_eff_pct(idx, trail_mode, atr_series, closes,
                                 trail_atr_k, trail_pct)
            )

        if holding_shares > 0 and (not signal or stop_triggered):
            sell_price = close
            gross = holding_shares * sell_price
            fee = gross * (commission_rate + stamp_duty_rate)
            net_proceeds = gross - fee
            profit_rate = (sell_price * (1 - commission_rate - stamp_duty_rate)
                           - buy_price) / buy_price if buy_price > 0 else 0.0
            trade_records.append({
                "buyDate": buy_date,
                "sellDate": date,
                "etfCode": stock_code,
                "buyPrice": round(buy_price_raw, 4),
                "sellPrice": round(sell_price, 4),
                "shares": holding_shares,
                "profitRate": round(profit_rate, 4),
                "fee": round(fee, 2),
                "reason": "跟踪止损" if stop_triggered else "条件不满足",
            })
            capital += net_proceeds
            holding_shares = 0
            buy_price = 0.0
            buy_price_raw = 0.0
            buy_date = None
            max_close_since_entry = 0.0
        elif holding_shares == 0 and signal and market_ok:
            px = close
            shares = int(capital / (px * (1 + commission_rate))) if px > 0 else 0
            if shares > 0:
                cost = shares * px
                fee = cost * commission_rate
                capital -= (cost + fee)
                holding_shares = shares
                buy_price_raw = px
                buy_price = px * (1 + commission_rate)
                buy_date = date
                max_close_since_entry = px  # 棘轮初始化为买入价

        # 持仓中更新棘轮最高（不下降，仅上调）
        if holding_shares > 0 and close > max_close_since_entry:
            max_close_since_entry = close

        equity = holding_shares * close + capital
        equity_curve.append((date, round(equity, 2)))

    # ── 当前持仓 ──
    current_holding = None
    if holding_shares > 0 and in_range_idx:
        last_idx = in_range_idx[-1]
        current_price = closes[last_idx]
        current_value = holding_shares * current_price + capital
        if buy_price > 0:
            sell_net_px = current_price * (1 - commission_rate - stamp_duty_rate)
            unrealized = (sell_net_px - buy_price) / buy_price
        else:
            unrealized = 0.0
        holding_days = 0
        if buy_date:
            try:
                bi = next(i for i in in_range_idx if dates[i] == buy_date)
                holding_days = in_range_idx.index(last_idx) - in_range_idx.index(bi)
            except StopIteration:
                pass
        current_holding = {
            "etfCode": stock_code,
            "buyDate": buy_date,
            "buyPrice": round(buy_price_raw, 4),
            "currentPrice": round(current_price, 4),
            "shares": holding_shares,
            "currentValue": round(current_value, 2),
            "unrealizedProfit": round(unrealized, 4),
            "holdingDays": holding_days,
        }

    # ── 买入持有基准 ──
    benchmark_curve = []
    if in_range_idx:
        first_idx = in_range_idx[0]
        bench_px = closes[first_idx]
        bench_shares = int(initial_capital / (bench_px * (1 + commission_rate))) if bench_px > 0 else 0
        bench_cost = bench_shares * bench_px
        bench_fee = bench_cost * commission_rate
        bench_cash = float(initial_capital) - bench_cost - bench_fee
        for i in in_range_idx:
            v = bench_shares * closes[i] + bench_cash
            benchmark_curve.append((dates[i], round(v, 2)))

    # ── 图表数据 ──
    chart_dates = [dates[i] for i in in_range_idx]
    kline = [[dates[i], opens[i], highs[i], lows[i], closes[i]] for i in in_range_idx]
    volume_bars = [
        [dates[i], volumes[i], 1 if closes[i] >= opens[i] else -1]
        for i in in_range_idx
    ]

    def pick(series):
        return [
            (round(series[i], 4) if series[i] is not None else None)
            for i in in_range_idx
        ]

    def pick_flags(flags):
        return [bool(flags[i]) for i in in_range_idx]

    chart_data = {
        "dates": chart_dates,
        "kline": kline,
        "trend_ma_short": pick(trend_ma_short),
        "trend_ma_long": pick(trend_ma_long),
        "volumes": volume_bars,
        "vol_ma_recent": pick(vol_ma_recent),  # 近 flow_period 日均量（量比分子）
        "vol_ma_basis": pick(vol_ma_basis),    # 近 ratio_period 日均量（量比分母）
        "momentum_pct": pick(momentum_pct),    # 动量百分比折线
        "drawdowns": pick(drawdowns),          # 回撤序列（负数）
        "flags": {
            "trend": pick_flags(trend_flags),
            "momentum": pick_flags(momentum_flags),
            "volprice": pick_flags(volprice_flags),
            "risk": pick_flags(risk_flags),
            "all": pick_flags(all_flags),
        },
        "equity": [v for _, v in equity_curve],
        "benchmark": [v for _, v in benchmark_curve],
        "market_closes": [
            (round(market_closes[i], 4) if market_closes and market_closes[i] is not None else None)
            for i in in_range_idx
        ] if market_filter_enabled and market_closes else [],
        "market_ma": [
            (round(market_ma[i], 4) if market_ma[i] is not None else None)
            for i in in_range_idx
        ] if market_filter_enabled else [],
        "market_gate": [
            bool(market_gate_flags[i]) for i in in_range_idx
        ] if market_filter_enabled else [],
    }

    # ── benchmark 指标 ──
    if benchmark_curve:
        bench_final = benchmark_curve[-1][1]
        bench_total_return = (bench_final - initial_capital) / initial_capital
        bench_annualized = calculate_annualized_return(benchmark_curve, initial_capital)
        bench_max_dd = calculate_max_drawdown(benchmark_curve)
    else:
        bench_final = initial_capital
        bench_total_return = 0.0
        bench_annualized = 0.0
        bench_max_dd = 0.0

    extra = {
        "start_date": chart_dates[0] if chart_dates else start_date,
        "end_date": chart_dates[-1] if chart_dates else start_date,
        "stock_code": stock_code,
        "trend_enabled": trend_enabled,
        "trend_short_period": trend_short_period,
        "trend_long_period": trend_long_period,
        "momentum_enabled": momentum_enabled,
        "momentum_period": momentum_period,
        "volprice_enabled": volprice_enabled,
        "volprice_ratio_period": volprice_ratio_period,
        "volprice_flow_period": volprice_flow_period,
        "volprice_ratio_threshold": volprice_ratio_threshold,
        "risk_enabled": risk_enabled,
        "risk_lookback": risk_lookback,
        "risk_drawdown_threshold": risk_drawdown_threshold,
        "risk_mode": risk_mode,
        "risk_atr_k": risk_atr_k,
        "risk_eff_avg": (
            round(
                sum(
                    risk_eff_thresh[i] for i in in_range_idx
                    if risk_eff_thresh[i] is not None
                ) / max(1, sum(1 for i in in_range_idx if risk_eff_thresh[i] is not None)),
                4,
            )
            if any(risk_eff_thresh[i] is not None for i in in_range_idx) else None
        ),
        "atr_period": atr_period,
        "min_match_count": min_match_count,
        "n_enabled_dimensions": sum(1 for v in enabled.values() if v),
        "trailing_stop_enabled": trailing_stop_enabled,
        "trail_pct": trail_pct,
        "trail_mode": trail_mode,
        "trail_atr_k": trail_atr_k,
        "trail_eff_avg": (round(sum(trail_eff_during_hold) / len(trail_eff_during_hold), 4)
                          if trail_eff_during_hold else None),
        "trailing_stop_exits": sum(1 for t in trade_records if t.get("reason") == "跟踪止损"),
        "market_filter_enabled": market_filter_enabled,
        "market_ma_period": market_ma_period,
        "market_gate_blocked_days": (
            sum(1 for f in market_gate_flags[in_range_idx[0]:in_range_idx[-1] + 1] if not f)
            if market_filter_enabled and in_range_idx else 0
        ),
        "commission_rate": commission_rate,
        "stamp_duty_rate": stamp_duty_rate,
        "benchmark_final_equity": bench_final,
        "benchmark_total_return": round(bench_total_return, 4),
        "benchmark_annualized_return": bench_annualized,
        "benchmark_max_drawdown": bench_max_dd,
    }
    summary = build_summary(equity_curve, trade_records, initial_capital, extra=extra)
    summary["alpha_total_return"] = round(summary["total_return"] - bench_total_return, 4)
    summary["alpha_annualized_return"] = round(
        (summary.get("annualized_return") or 0.0) - bench_annualized, 4)

    return {
        "equity_curve": equity_curve,
        "benchmark_curve": benchmark_curve,
        "trade_records": trade_records,
        "current_holding": current_holding,
        "summary": summary,
        "chart_data": chart_data,
        "dimension_params": {
            "trend": {"enabled": trend_enabled,
                      "short": trend_short_period, "long": trend_long_period},
            "momentum": {"enabled": momentum_enabled, "period": momentum_period},
            "volprice": {"enabled": volprice_enabled,
                         "ratio_period": volprice_ratio_period,
                         "flow_period": volprice_flow_period,
                         "threshold": volprice_ratio_threshold},
            "risk": {"enabled": risk_enabled,
                     "lookback": risk_lookback,
                     "drawdown": risk_drawdown_threshold},
        },
    }


def _empty_result(initial_capital, stock_code):
    summary = build_summary([], [], initial_capital, extra={"stock_code": stock_code})
    return {
        "equity_curve": [],
        "benchmark_curve": [],
        "trade_records": [],
        "current_holding": None,
        "summary": summary,
        "chart_data": {
            "dates": [], "kline": [],
            "trend_ma_short": [], "trend_ma_long": [],
            "volumes": [], "vol_ma_recent": [], "vol_ma_basis": [],
            "momentum_pct": [], "drawdowns": [],
            "flags": {"trend": [], "momentum": [], "volprice": [], "risk": [], "all": []},
            "equity": [], "benchmark": [],
            "market_closes": [], "market_ma": [], "market_gate": [],
        },
        "dimension_params": {},
    }

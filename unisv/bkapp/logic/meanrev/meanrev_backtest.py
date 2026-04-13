"""均值回归策略回测。

策略逻辑：
  1. 每个调仓日，计算所有 ETF 的偏离度
  2. 找到最超卖（偏离度最负）的标的
  3. 如果偏离度低于买入阈值（跌破下轨），买入
  4. 持仓标的回到中轨以上时卖出
  5. 持仓标的继续下跌超过止损比例时止损
"""
import numpy as np
from .signal import compute_signal, compute_deviation
from ..common.metrics import build_summary


def run_meanrev_backtest(etf_history_dict, start_date, end_date=None,
                         initial_capital=1000000,
                         signal_type='bollinger',
                         period=20, num_std=2.0,
                         stop_loss=0.05,
                         rebalance_days=1,
                         oversold=30, overbought=70):
    """执行均值回归回测。

    Args:
        etf_history_dict: {etf_code: [[date_str, open, high, low, close, volume], ...]}
        start_date: 回测起始日期 'YYYY/MM/DD'
        end_date: 回测结束日期
        initial_capital: 初始资金
        signal_type: 信号类型 'bollinger' 或 'rsi'
        period: 指标周期（布林带MA天数 / RSI天数）
        num_std: 布林带标准差倍数
        stop_loss: 止损比例（0.05 = 跌5%止损）
        rebalance_days: 调仓检查周期
        oversold: RSI 超卖阈值（默认30）
        overbought: RSI 超买阈值（默认70）

    Returns:
        dict: 和动量轮动相同的标准输出格式
    """
    etf_codes = list(etf_history_dict.keys())

    # 构建价格映射
    etf_close = {}
    for code in etf_codes:
        etf_close[code] = {row[0]: row[4] for row in etf_history_dict[code]}

    # 所有 ETF 共同交易日
    date_sets = [set(etf_close[code].keys()) for code in etf_codes]
    common_dates = sorted(set.intersection(*date_sets))

    trade_dates = [d for d in common_dates if d >= start_date and (end_date is None or d <= end_date)]
    all_dates = common_dates

    if len(trade_dates) == 0:
        return {"equity_curve": [], "deviation_curves": {}, "trade_records": [],
                "summary": {}}

    # 按 common_dates 排序的收盘价序列
    etf_close_series = {}
    for code in etf_codes:
        etf_close_series[code] = [etf_close[code][d] for d in all_dates]

    date_to_idx = {d: i for i, d in enumerate(all_dates)}

    # 信号参数
    signal_params = {'period': period, 'num_std': num_std}
    if signal_type == 'rsi':
        signal_params = {'period': period, 'oversold': oversold, 'overbought': overbought}

    # 回测变量
    capital = initial_capital
    holding_code = None
    holding_shares = 0
    buy_price = 0
    buy_date = None

    equity_curve = []
    deviation_curves = {code: [] for code in etf_codes}
    trade_records = []

    # RSI 需要 period+1 个数据点（因为要做 diff），布林带只需要 period 个
    window_size = period + 1 if signal_type == 'rsi' else period
    min_idx = window_size - 1

    days_since_check = rebalance_days  # 确保第一天触发

    for date in trade_dates:
        idx = date_to_idx[date]

        # 当日持仓市值
        if holding_code and holding_shares > 0:
            current_price = etf_close[holding_code][date]
            equity = holding_shares * current_price + capital
        else:
            equity = capital

        # 计算各 ETF 的偏离度
        deviations = {}
        for code in etf_codes:
            if idx >= min_idx:
                prices_window = etf_close_series[code][idx - window_size + 1:idx + 1]
                dev = compute_deviation(prices_window, signal_type=signal_type, **signal_params)
                deviations[code] = dev
                deviation_curves[code].append((date, round(dev, 4)))
            else:
                deviation_curves[code].append((date, None))

        days_since_check += 1

        # 止损检查（每天都检查，不受调仓周期限制）
        if holding_code and holding_shares > 0:
            current_price = etf_close[holding_code][date]
            loss_rate = (current_price - buy_price) / buy_price
            if loss_rate < -stop_loss:
                # 止损卖出
                sell_amount = holding_shares * current_price
                trade_records.append({
                    "buyDate": buy_date,
                    "sellDate": date,
                    "etfCode": holding_code,
                    "buyPrice": round(buy_price, 4),
                    "sellPrice": round(current_price, 4),
                    "shares": holding_shares,
                    "profitRate": round(loss_rate, 4),
                    "reason": f"止损({round(loss_rate*100,1)}%)",
                })
                capital = sell_amount
                holding_code = None
                holding_shares = 0
                equity = capital
                days_since_check = rebalance_days  # 重置，下次立即检查

        # 调仓日检查
        if days_since_check >= rebalance_days:
            days_since_check = 0

            if holding_code and holding_shares > 0:
                # 已有持仓：检查是否应该卖出（回到中轨）
                if idx >= min_idx:
                    prices_window = etf_close_series[holding_code][idx - window_size + 1:idx + 1]
                    sig = compute_signal(prices_window, signal_type=signal_type, **signal_params)
                    if sig['action'] == 'sell':
                        sell_price = etf_close[holding_code][date]
                        sell_amount = holding_shares * sell_price
                        profit_rate = (sell_price - buy_price) / buy_price
                        trade_records.append({
                            "buyDate": buy_date,
                            "sellDate": date,
                            "etfCode": holding_code,
                            "buyPrice": round(buy_price, 4),
                            "sellPrice": round(sell_price, 4),
                            "shares": holding_shares,
                            "profitRate": round(profit_rate, 4),
                            "reason": sig['reason'],
                        })
                        capital = sell_amount
                        holding_code = None
                        holding_shares = 0
                        equity = capital
            else:
                # 空仓：找最超卖的标的
                if deviations:
                    # 只考虑有买入信号的标的
                    buy_candidates = {}
                    for code, dev in deviations.items():
                        if idx >= min_idx:
                            prices_window = etf_close_series[code][idx - window_size + 1:idx + 1]
                            sig = compute_signal(prices_window, signal_type=signal_type, **signal_params)
                            if sig['action'] == 'buy':
                                buy_candidates[code] = dev

                    if buy_candidates:
                        # 选偏离度最负的（最超卖的）
                        best_code = min(buy_candidates, key=lambda c: buy_candidates[c])
                        buy_price = etf_close[best_code][date]
                        holding_shares = int(capital / buy_price)
                        if holding_shares > 0:
                            capital_used = holding_shares * buy_price
                            capital = capital - capital_used
                            holding_code = best_code
                            buy_date = date
                            equity = holding_shares * buy_price + capital

        equity_curve.append((date, round(equity, 2)))

    # 当前持仓信息
    current_holding = None
    if holding_code and holding_shares > 0 and trade_dates:
        last_date = trade_dates[-1]
        current_price = etf_close[holding_code][last_date]
        current_value = holding_shares * current_price + capital
        unrealized_profit = (current_price - buy_price) / buy_price
        current_holding = {
            "etfCode": holding_code,
            "buyDate": buy_date,
            "buyPrice": round(buy_price, 4),
            "currentPrice": round(current_price, 4),
            "shares": holding_shares,
            "currentValue": round(current_value, 2),
            "unrealizedProfit": round(unrealized_profit, 4),
            "holdingDays": trade_dates.index(last_date) - trade_dates.index(buy_date) if buy_date in trade_dates else 0,
        }

    extra = {
        "start_date": trade_dates[0] if trade_dates else start_date,
        "end_date": trade_dates[-1] if trade_dates else start_date,
        "signal_type": signal_type,
        "period": period,
        "stop_loss": stop_loss,
        "rebalance_days": rebalance_days,
        "etf_codes": etf_codes,
    }
    if signal_type == 'bollinger':
        extra["num_std"] = num_std
    else:
        extra["oversold"] = oversold
        extra["overbought"] = overbought

    summary = build_summary(equity_curve, trade_records, initial_capital, extra=extra)

    return {
        "equity_curve": equity_curve,
        "deviation_curves": deviation_curves,
        "trade_records": trade_records,
        "current_holding": current_holding,
        "summary": summary,
    }

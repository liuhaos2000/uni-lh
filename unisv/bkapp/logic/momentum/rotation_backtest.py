import numpy as np
from .momentum_score import calculate_momentum_score
from .decision import decide_signal


def run_rotation_backtest(etf_history_dict, start_date, end_date=None,
                          initial_capital=1000000, lookback_n=25, rebalance_days=5):
    """执行动量轮动回测。

    Args:
        etf_history_dict: {etf_code: [(date_str, open, high, low, close, volume), ...]}
            每个ETF的历史日线数据，按日期升序排列
        start_date: 回测起始日期字符串，格式 'YYYY/MM/DD'
        end_date: 回测结束日期字符串，格式 'YYYY/MM/DD'，默认None表示到最后
        initial_capital: 初始资金，默认100万
        lookback_n: 动量回看天数，默认25
        rebalance_days: 调仓周期（交易日），默认5

    Returns:
        dict: {
            "equity_curve": [(date, equity), ...],
            "momentum_curves": {etf_code: [(date, score), ...], ...},
            "trade_records": [{...}, ...],
            "summary": {...}
        }
    """
    etf_codes = list(etf_history_dict.keys())

    # 构建每个ETF的 {date: close_price} 和 {date: open_price} 映射
    etf_close = {}
    etf_open = {}
    for code in etf_codes:
        etf_close[code] = {row[0]: row[4] for row in etf_history_dict[code]}
        etf_open[code] = {row[0]: row[1] for row in etf_history_dict[code]}

    # 取所有ETF共同的交易日期，并排序
    date_sets = [set(etf_close[code].keys()) for code in etf_codes]
    common_dates = sorted(set.intersection(*date_sets))

    # 筛选 >= start_date 且 <= end_date 的日期
    trade_dates = [d for d in common_dates if d >= start_date and (end_date is None or d <= end_date)]
    # 回看数据需要 start_date 之前的日期
    all_dates = common_dates

    if len(trade_dates) == 0:
        return {"equity_curve": [], "momentum_curves": {}, "trade_records": [],
                "summary": {}}

    # 构建每个ETF按 common_dates 排序的收盘价序列（含回看期）
    etf_close_series = {}
    for code in etf_codes:
        etf_close_series[code] = [etf_close[code][d] for d in all_dates]

    # 日期到索引的映射
    date_to_idx = {d: i for i, d in enumerate(all_dates)}

    # 回测变量
    capital = initial_capital
    holding_code = None       # 当前持仓ETF代码
    holding_shares = 0        # 持仓份数
    buy_price = 0             # 买入价格
    buy_date = None           # 买入日期

    equity_curve = []
    momentum_curves = {code: [] for code in etf_codes}
    trade_records = []

    days_since_rebalance = rebalance_days  # 初始值设为调仓周期，确保第一天触发
    last_signal = None       # 最后一个交易日的信号
    last_scores = {}          # 最后一个交易日的评分

    for date in trade_dates:
        idx = date_to_idx[date]

        # 计算当日持仓市值
        if holding_code and holding_shares > 0:
            current_price = etf_close[holding_code][date]
            equity = holding_shares * current_price
        else:
            equity = capital

        # 计算各ETF的动量评分
        scores = {}
        for code in etf_codes:
            if idx >= lookback_n - 1:
                prices_window = etf_close_series[code][idx - lookback_n + 1:idx + 1]
                score = calculate_momentum_score(prices_window, lookback_n)
                scores[code] = score
                momentum_curves[code].append((date, round(score, 6) if score is not None else None))
            else:
                momentum_curves[code].append((date, None))

        days_since_rebalance += 1

        # 通过纯函数决策
        signal = decide_signal(scores, holding_code, days_since_rebalance, rebalance_days)
        last_signal = signal
        last_scores = scores

        if signal['is_rebalance_day']:
            days_since_rebalance = 0
            action = signal['action']
            target_code = signal['target_code']

            # 卖出 / 换仓 都需要先平掉当前持仓
            if action in ('sell', 'swap') and holding_code and holding_shares > 0:
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
                    "reason": signal['reason'],
                })
                capital = sell_amount
                holding_code = None
                holding_shares = 0
                equity = capital

            # 换仓 / 建仓 需要买入目标标的
            if action in ('swap', 'buy') and target_code:
                buy_price = etf_close[target_code][date]
                holding_shares = int(capital / buy_price)
                capital_used = holding_shares * buy_price
                capital = capital - capital_used  # 剩余零头
                holding_code = target_code
                buy_date = date
                equity = holding_shares * buy_price + capital

        # 记录权益曲线
        equity_curve.append((date, round(equity, 2)))

    # 回测结束，计算最终状态
    final_equity = equity_curve[-1][1] if equity_curve else initial_capital
    total_return = (final_equity - initial_capital) / initial_capital

    # 计算夏普比率（年化，无风险利率按2.5%）
    sharpe_ratio = _calculate_sharpe(equity_curve, risk_free_rate=0.025)

    # 最大回撤
    max_drawdown = _calculate_max_drawdown(equity_curve)

    # Calmar 比率（年化收益 / 最大回撤）
    annualized_return = _calculate_annualized_return(equity_curve, initial_capital)
    calmar_ratio = round(annualized_return / abs(max_drawdown), 4) if max_drawdown < 0 else 0.0

    # 胜率（已平仓交易里赚钱的占比）
    if trade_records:
        wins = sum(1 for t in trade_records if t.get('profitRate', 0) > 0)
        win_rate = round(wins / len(trade_records), 4)
    else:
        win_rate = 0.0

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

    summary = {
        "initial_capital": initial_capital,
        "final_equity": final_equity,
        "total_return": round(total_return, 4),
        "annualized_return": annualized_return,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "calmar_ratio": calmar_ratio,
        "win_rate": win_rate,
        "total_trades": len(trade_records),
        "start_date": trade_dates[0] if trade_dates else start_date,
        "end_date": trade_dates[-1] if trade_dates else start_date,
        "lookback_n": lookback_n,
        "rebalance_days": rebalance_days,
        "etf_codes": etf_codes,
    }

    return {
        "equity_curve": equity_curve,
        "momentum_curves": momentum_curves,
        "trade_records": trade_records,
        "current_holding": current_holding,
        "summary": summary,
        "latest_signal": last_signal,
        "latest_scores": {k: (round(v, 6) if v is not None else None) for k, v in last_scores.items()},
        "latest_date": trade_dates[-1] if trade_dates else None,
    }


def _calculate_sharpe(equity_curve, risk_free_rate=0.025):
    """根据权益曲线计算年化夏普比率。

    Args:
        equity_curve: [(date, equity), ...]
        risk_free_rate: 年化无风险利率，默认2.5%

    Returns:
        float: 年化夏普比率，数据不足时返回 0
    """
    if len(equity_curve) < 2:
        return 0.0

    equities = np.array([e[1] for e in equity_curve], dtype=float)
    # 日收益率
    daily_returns = np.diff(equities) / equities[:-1]

    if len(daily_returns) == 0 or np.std(daily_returns) == 0:
        return 0.0

    # 年化（约242个交易日）
    trading_days = 242
    daily_rf = risk_free_rate / trading_days
    excess_returns = daily_returns - daily_rf

    sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(trading_days)
    return round(float(sharpe), 4)


def _calculate_max_drawdown(equity_curve):
    """计算最大回撤（以负数返回，例如 -0.225 表示 -22.5%）。"""
    if len(equity_curve) < 2:
        return 0.0
    equities = np.array([e[1] for e in equity_curve], dtype=float)
    running_max = np.maximum.accumulate(equities)
    drawdowns = (equities - running_max) / running_max
    return round(float(drawdowns.min()), 4)


def _calculate_annualized_return(equity_curve, initial_capital):
    """根据权益曲线计算年化收益率。"""
    if len(equity_curve) < 2:
        return 0.0
    final = equity_curve[-1][1]
    total_return = (final - initial_capital) / initial_capital
    days = len(equity_curve)
    years = days / 242.0
    if years <= 0:
        return 0.0
    try:
        ann = (1 + total_return) ** (1 / years) - 1
    except (ValueError, ZeroDivisionError):
        return 0.0
    return round(float(ann), 4)

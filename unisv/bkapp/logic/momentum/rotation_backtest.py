import numpy as np
from .momentum_score import calculate_momentum_score
from .decision import decide_signal_multi
from ..common.metrics import build_summary


def run_rotation_backtest(etf_history_dict, start_date, end_date=None,
                          initial_capital=1000000, lookback_n=25, rebalance_days=5,
                          ma_period=0, position_weights=None):
    """执行动量轮动回测（支持 Top-N 多仓）。

    Args:
        etf_history_dict: {etf_code: [(date_str, open, high, low, close, volume), ...]}
        start_date: 回测起始日期字符串
        end_date: 回测结束日期字符串
        initial_capital: 初始资金，默认100万
        lookback_n: 动量回看天数
        rebalance_days: 调仓周期（交易日）
        ma_period: 均线过滤周期，0 表示不启用
        position_weights: 各名次仓位权重列表，如 [0.5, 0.3, 0.2]。
            长度即 top_n；默认 [1.0] 表示仅买入第一名、全仓。

    Returns:
        dict: {
            "equity_curve": [(date, equity), ...],
            "momentum_curves": {etf_code: [(date, score), ...], ...},
            "trade_records": [{...}, ...],
            "current_holdings": [{...}, ...],
            "summary": {...},
            ...
        }
    """
    if not position_weights:
        position_weights = [1.0]
    position_weights = [float(w) for w in position_weights]
    top_n = len(position_weights)

    etf_codes = list(etf_history_dict.keys())

    etf_close = {}
    etf_open = {}
    for code in etf_codes:
        etf_close[code] = {row[0]: row[4] for row in etf_history_dict[code]}
        etf_open[code] = {row[0]: row[1] for row in etf_history_dict[code]}

    date_sets = [set(etf_close[code].keys()) for code in etf_codes]
    common_dates = sorted(set.intersection(*date_sets))

    trade_dates = [d for d in common_dates if d >= start_date and (end_date is None or d <= end_date)]
    all_dates = common_dates

    if len(trade_dates) == 0:
        return {"equity_curve": [], "momentum_curves": {}, "trade_records": [],
                "summary": {}}

    etf_close_series = {}
    for code in etf_codes:
        etf_close_series[code] = [etf_close[code][d] for d in all_dates]

    date_to_idx = {d: i for i, d in enumerate(all_dates)}

    # 回测变量 ——— 多仓
    capital = initial_capital
    # holdings: {code: {shares, buy_price, buy_date, rank, weight}}
    holdings = {}

    equity_curve = []
    momentum_curves = {code: [] for code in etf_codes}
    trade_records = []

    days_since_rebalance = rebalance_days
    last_signal = None
    last_scores = {}

    def compute_equity(date):
        val = capital
        for code, h in holdings.items():
            val += h['shares'] * etf_close[code][date]
        return val

    for date in trade_dates:
        idx = date_to_idx[date]

        # 当日评分
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

        above_ma = None
        if ma_period > 0:
            above_ma = {}
            for code in etf_codes:
                if idx >= ma_period - 1:
                    ma_val = np.mean(etf_close_series[code][idx - ma_period + 1:idx + 1])
                    above_ma[code] = etf_close[code][date] >= ma_val
                else:
                    above_ma[code] = True

        signal = decide_signal_multi(
            scores, list(holdings.keys()), days_since_rebalance, rebalance_days,
            top_n=top_n, above_ma=above_ma,
        )
        last_signal = signal
        last_scores = scores

        if signal['is_rebalance_day']:
            days_since_rebalance = 0
            action = signal['action']
            target_codes = signal.get('target_codes') or []
            target_rank = {code: i for i, code in enumerate(target_codes)}

            # 需要卖出的代码：当前持有但不在新目标里（包括 action=='sell' 时全清）
            if action == 'sell':
                codes_to_sell = list(holdings.keys())
            elif action == 'rebalance':
                codes_to_sell = [c for c in holdings.keys() if c not in target_rank]
            else:
                codes_to_sell = []

            for code in codes_to_sell:
                h = holdings[code]
                sell_price = etf_close[code][date]
                sell_amount = h['shares'] * sell_price
                profit_rate = (sell_price - h['buy_price']) / h['buy_price'] if h['buy_price'] else 0
                trade_records.append({
                    "buyDate": h['buy_date'],
                    "sellDate": date,
                    "etfCode": code,
                    "buyPrice": round(h['buy_price'], 4),
                    "sellPrice": round(sell_price, 4),
                    "shares": h['shares'],
                    "profitRate": round(profit_rate, 4),
                    "rank": h.get('rank'),
                    "weight": h.get('weight'),
                    "reason": signal['reason'],
                })
                capital += sell_amount
                del holdings[code]

            # 刷新保留持仓的 rank/weight 标签（仅展示用，不改动仓位）
            if action == 'rebalance':
                for rank_i, code in enumerate(target_codes):
                    if code in holdings:
                        holdings[code]['rank'] = rank_i
                        holdings[code]['weight'] = position_weights[rank_i]

            # 买入：目标中当前未持有的代码，按 weight[rank] * initial_capital 预算
            if action == 'rebalance':
                for rank_i, code in enumerate(target_codes):
                    if code in holdings:
                        continue
                    weight = position_weights[rank_i]
                    target_budget = weight * initial_capital
                    budget = min(target_budget, capital)
                    if budget <= 0:
                        continue
                    buy_price = etf_close[code][date]
                    shares = int(budget / buy_price)
                    if shares <= 0:
                        continue
                    cost = shares * buy_price
                    capital -= cost
                    holdings[code] = {
                        'shares': shares,
                        'buy_price': buy_price,
                        'buy_date': date,
                        'rank': rank_i,
                        'weight': weight,
                    }

        equity_curve.append((date, round(compute_equity(date), 2)))

    summary = build_summary(equity_curve, trade_records, initial_capital, extra={
        "start_date": trade_dates[0] if trade_dates else start_date,
        "end_date": trade_dates[-1] if trade_dates else start_date,
        "lookback_n": lookback_n,
        "rebalance_days": rebalance_days,
        "ma_period": ma_period,
        "etf_codes": etf_codes,
        "position_weights": position_weights,
        "top_n": top_n,
    })

    current_holdings = []
    if holdings and trade_dates:
        last_date = trade_dates[-1]
        for code, h in sorted(holdings.items(), key=lambda kv: kv[1].get('rank', 0)):
            current_price = etf_close[code][last_date]
            current_value = h['shares'] * current_price
            unrealized_profit = (current_price - h['buy_price']) / h['buy_price'] if h['buy_price'] else 0
            holding_days = 0
            if h['buy_date'] in trade_dates:
                holding_days = trade_dates.index(last_date) - trade_dates.index(h['buy_date'])
            current_holdings.append({
                "etfCode": code,
                "buyDate": h['buy_date'],
                "buyPrice": round(h['buy_price'], 4),
                "currentPrice": round(current_price, 4),
                "shares": h['shares'],
                "currentValue": round(current_value, 2),
                "unrealizedProfit": round(unrealized_profit, 4),
                "holdingDays": holding_days,
                "rank": h.get('rank'),
                "weight": h.get('weight'),
            })

    # 兼容旧前端字段：top_n==1 时附带单持仓 current_holding
    current_holding = None
    if top_n == 1 and current_holdings:
        ch = current_holdings[0]
        current_holding = {
            "etfCode": ch['etfCode'],
            "buyDate": ch['buyDate'],
            "buyPrice": ch['buyPrice'],
            "currentPrice": ch['currentPrice'],
            "shares": ch['shares'],
            "currentValue": round(ch['currentValue'] + capital, 2),
            "unrealizedProfit": ch['unrealizedProfit'],
            "holdingDays": ch['holdingDays'],
        }

    return {
        "equity_curve": equity_curve,
        "momentum_curves": momentum_curves,
        "trade_records": trade_records,
        "current_holdings": current_holdings,
        "current_holding": current_holding,
        "cash": round(capital, 2),
        "summary": summary,
        "latest_signal": last_signal,
        "latest_scores": {k: (round(v, 6) if v is not None else None) for k, v in last_scores.items()},
        "latest_date": trade_dates[-1] if trade_dates else None,
        "position_weights": position_weights,
        "top_n": top_n,
    }

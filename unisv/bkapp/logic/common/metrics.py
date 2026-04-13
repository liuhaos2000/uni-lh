"""策略回测通用指标计算。

所有策略共用的绩效指标：夏普比率、最大回撤、年化收益、胜率等。
"""
import numpy as np

TRADING_DAYS_PER_YEAR = 242


def calculate_sharpe(equity_curve, risk_free_rate=0.025):
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
    daily_returns = np.diff(equities) / equities[:-1]

    if len(daily_returns) == 0 or np.std(daily_returns) == 0:
        return 0.0

    daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR
    excess_returns = daily_returns - daily_rf

    sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(TRADING_DAYS_PER_YEAR)
    return round(float(sharpe), 4)


def calculate_max_drawdown(equity_curve):
    """计算最大回撤（以负数返回，例如 -0.225 表示 -22.5%）。"""
    if len(equity_curve) < 2:
        return 0.0
    equities = np.array([e[1] for e in equity_curve], dtype=float)
    running_max = np.maximum.accumulate(equities)
    drawdowns = (equities - running_max) / running_max
    return round(float(drawdowns.min()), 4)


def calculate_annualized_return(equity_curve, initial_capital):
    """根据权益曲线计算年化收益率。"""
    if len(equity_curve) < 2:
        return 0.0
    final = equity_curve[-1][1]
    total_return = (final - initial_capital) / initial_capital
    days = len(equity_curve)
    years = days / float(TRADING_DAYS_PER_YEAR)
    if years <= 0:
        return 0.0
    try:
        ann = (1 + total_return) ** (1 / years) - 1
    except (ValueError, ZeroDivisionError):
        return 0.0
    return round(float(ann), 4)


def calculate_win_rate(trade_records):
    """计算胜率（已平仓交易里赚钱的占比）。"""
    if not trade_records:
        return 0.0
    wins = sum(1 for t in trade_records if t.get('profitRate', 0) > 0)
    return round(wins / len(trade_records), 4)


def build_summary(equity_curve, trade_records, initial_capital, extra=None):
    """构建通用的回测结果 summary。

    Args:
        equity_curve: [(date, equity), ...]
        trade_records: [{"profitRate": ..., ...}, ...]
        initial_capital: 初始资金
        extra: dict, 额外字段（策略特有参数等）

    Returns:
        dict: 标准化的 summary
    """
    final_equity = equity_curve[-1][1] if equity_curve else initial_capital
    total_return = (final_equity - initial_capital) / initial_capital

    annualized_return = calculate_annualized_return(equity_curve, initial_capital)
    max_drawdown = calculate_max_drawdown(equity_curve)
    calmar = round(annualized_return / abs(max_drawdown), 4) if max_drawdown < 0 else 0.0

    summary = {
        "initial_capital": initial_capital,
        "final_equity": final_equity,
        "total_return": round(total_return, 4),
        "annualized_return": annualized_return,
        "sharpe_ratio": calculate_sharpe(equity_curve),
        "max_drawdown": max_drawdown,
        "calmar_ratio": calmar,
        "win_rate": calculate_win_rate(trade_records),
        "total_trades": len(trade_records),
    }
    if extra:
        summary.update(extra)
    return summary

# backtest/strategies/base.py
import pandas as pd

class StrategyBase:
    value = '00'
    name = 'base'
    params = []
    level = 'normal'  # 'normal' 或 'vip'

    def __init__(self, **kwargs):
        """
        初始化策略通用属性
        """
        # 参数注入
        self.total_parts = kwargs.get("total_parts", 50)  # 仓位拆分数量
        self.lookback = kwargs.get("lookback", 3)         # 回看天数
        self.take_profit_pct = kwargs.get("take_profit_pct", None)  # 单笔止盈比例
        self.stop_loss_pct = kwargs.get("stop_loss_pct", None)      # 单笔止损比例

        # 回测状态
        self.position_parts = 0
        self.history_list = []
        self.mark_points = []
        self.total_profit = 0.0

    # ----------------- 子类必须实现 -----------------
    def prepare(self, df):
        """策略指标计算，可选实现"""
        pass

    def generate_buy_signal(self, df, i):
        raise NotImplementedError

    def generate_sell_signal(self, df, i):
        raise NotImplementedError

    def check_take_profit(self, buy_price, current_price):
        """检查单笔止盈"""
        if self.take_profit_pct is None:
            return False
        return (current_price - buy_price) / buy_price >= self.take_profit_pct

    def check_stop_loss(self, buy_price, current_price):
        """检查单笔止损"""
        if self.stop_loss_pct is None:
            return False
        return (current_price - buy_price) / buy_price <= -self.stop_loss_pct

    # ----------------- 买入方法 -----------------
    def buy(self, date_str, price):
        self.position_parts += 1
        self.history_list.append({
            "buyDate": date_str,
            "buyPrice": price,
            "sellDate": "",
            "sellPrice": "",
            "warehousePosition": round(self.position_parts / self.total_parts, 2),
            "profitMargin": ""
        })
        self.mark_points.append({
            "name": "Buy",
            "coord": [date_str, price],
            "value": price,
            "itemStyle": {"color": "#00AA00"},
            "symbolSize": 30
        })

    # ----------------- 卖出方法 -----------------
    def sell(self, date_str, price, records_to_sell):
        for record in records_to_sell:
            profit = (price - record["buyPrice"]) / record["buyPrice"]
            record["sellDate"] = date_str
            record["sellPrice"] = price
            record["profitMargin"] = format(profit, ".4f")
            self.total_profit += profit * (1 / self.total_parts)
        self.position_parts -= len(records_to_sell)
        self.mark_points.append({
            "name": "Sell",
            "coord": [date_str, price],
            "value": price,
            "itemStyle": {"color": "#FF0000"},
            "symbolSize": 40
        })

    # ----------------- 回测方法 -----------------
    def backtest(self, history):
        df = pd.DataFrame(history, columns=["date", "open", "high", "low", "close"])
        df["date"] = pd.to_datetime(df["date"])

        self.prepare(df)

        for i in range(self.lookback, len(df)):
            today = df.iloc[i]
            date_str = today["date"].strftime("%Y/%m/%d")
            close_price = float(today["close"])

            # 买入信号
            if self.generate_buy_signal(df, i) and self.position_parts < self.total_parts:
                self.buy(date_str, close_price)

            # 卖出信号
            elif self.position_parts > 0:
                records_to_sell = []
                for record in self.history_list:
                    if record["sellDate"] == "":
                        # 止盈/止损或策略卖出信号
                        if self.check_take_profit(record["buyPrice"], close_price) or \
                           self.check_stop_loss(record["buyPrice"], close_price) or \
                           self.generate_sell_signal(df, i):
                            records_to_sell.append(record)
                if records_to_sell:
                    self.sell(date_str, close_price, records_to_sell)

        # 处理未卖出的仓位（浮动收益）
        last_close = float(df.iloc[-1]["close"])
        unclosed = [r for r in self.history_list if r["sellDate"] == ""]
        for record in unclosed:
            profit = (last_close - record["buyPrice"]) / record["buyPrice"]
            record["profitMargin"] = format(profit, ".4f")
            self.total_profit += profit * (1 / self.total_parts)

        # 汇总记录
        self.history_list.append({
            "buyDate": "",
            "buyPrice": "",
            "sellDate": "",
            "sellPrice": "",
            "warehousePosition": round(self.position_parts / self.total_parts, 2),
            "profitMargin": format(self.total_profit, ".4f")
        })

        return {
            "code": 0,
            "message": "success",
            "data": {
                "historyList": self.history_list,
                "markPoint": {"data": self.mark_points}
            }
        }

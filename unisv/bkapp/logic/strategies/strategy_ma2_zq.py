from .base import StrategyBase
import pandas as pd

class MovingAverageStrategy(StrategyBase):
    value = '004'
    name = 'EMA13_EMA34_ATR'
    params = []
    level = 'normal'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lookback = 34
        self.total_parts = 1

        # 固定参数
        self.fast = 13
        self.slow = 34
        self.atr_period = 20

        # 止损
        self.stop_loss_pct = 0.08

        # 移动止盈回撤
        self.trailing_stop_pct = 0.10

    # ----------------- 指标计算 -----------------
    def prepare(self, df):
        # EMA
        df["ema_fast"] = df["close"].ewm(span=self.fast, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=self.slow, adjust=False).mean()

        # True Range
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = tr.rolling(self.atr_period).mean()

        # ATR 80% 分位
        df["atr_q80"] = df["atr"].rolling(self.atr_period).quantile(0.8)

    # ----------------- 买入信号 -----------------
    def generate_buy_signal(self, df, i):
        if i < max(self.slow, self.atr_period) + 1:
            return False

        prev = df.iloc[i - 1]
        curr = df.iloc[i]

        # EMA 上穿
        ema_cross = prev["ema_fast"] <= prev["ema_slow"] and \
                    curr["ema_fast"] > curr["ema_slow"]

        # 波动率过滤
        atr_filter = curr["atr"] < curr["atr_q80"]

        return ema_cross and atr_filter

    # ----------------- 卖出信号（移动止盈） -----------------
    def generate_sell_signal(self, df, i):
        current_price = df.iloc[i]["close"]

        for record in self.history_list:
            if record["sellDate"] == "":
                # 初始化最高价
                if "max_price" not in record:
                    record["max_price"] = record["buyPrice"]

                # 更新最高价
                record["max_price"] = max(record["max_price"], current_price)

                # 回撤比例
                drawdown = (current_price - record["max_price"]) / record["max_price"]

                if drawdown <= -self.trailing_stop_pct:
                    return True

        return False
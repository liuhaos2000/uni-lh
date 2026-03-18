from .base import StrategyBase
import pandas as pd

class RsiStrategy(StrategyBase):
    value = '002'
    name = 'RSI'
    params = []
    level = 'normal'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rsi_period = 6
        self.take_profit_pct = 0.20  # 单笔止盈 10%
        self.stop_loss_pct = 0.10    # 单笔止损 10%
        self.lookback = 6
        self.total_parts = 1         # 

    def prepare(self, df):
        delta = df["close"].diff()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)

        period = self.rsi_period
        n = len(df)

        AU = pd.Series(0.0, index=df.index)
        AD = pd.Series(0.0, index=df.index)

        # 初始化第一条平滑值，用前 period 天的简单平均
        AU.iloc[period] = up.iloc[1:period+1].mean()
        AD.iloc[period] = down.iloc[1:period+1].mean()

        # 从 period+1 开始使用 Wilder 平滑公式
        for i in range(period + 1, n):
            AU.iloc[i] = (AU.iloc[i-1] * (period - 1) + up.iloc[i]) / period
            AD.iloc[i] = (AD.iloc[i-1] * (period - 1) + down.iloc[i]) / period

        # 计算 RSI
        RS = AU / AD
        df["RSI"] = 100 - 100 / (1 + RS)

        # 前 period 行没有足够数据，可以设置为 NaN 或用第 period 行填充
        df["RSI"].iloc[:period] = df["RSI"].iloc[period]
        print(df )

    def generate_buy_signal(self, df, i):
        return df.iloc[i]["RSI"] < 20

    def generate_sell_signal(self, df, i):
        # 卖出信号由止盈/止损触发，RSI>80 不再使用
        return False
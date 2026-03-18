from .base import StrategyBase
import pandas as pd

class MovingAverageStrategy(StrategyBase):
    value = '001'
    name = 'MA'
    params = ['fast', 'slow']
    level = 'normal'
    
    def __init__(self, fast=5, slow=10, **kwargs):
        super().__init__(fast=fast, slow=slow, **kwargs)
        self.fast = int(fast)
        self.slow = int(slow)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lookback = 3
        self.total_parts = 10

    def generate_buy_signal(self, df, i):
        prev_high = df.iloc[i-self.lookback:i]["high"].max()
        return df.iloc[i]["close"] > prev_high

    def generate_sell_signal(self, df, i):
        prev_low = df.iloc[i-self.lookback:i]["low"].min()
        return df.iloc[i]["close"] < prev_low
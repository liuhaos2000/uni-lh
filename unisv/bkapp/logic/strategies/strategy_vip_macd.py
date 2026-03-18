import numpy as np
from .base import StrategyBase

class RSIStrategy(StrategyBase):
    value = '101'
    name = 'MACD'
    params = ['period', 'lower', 'upper']
    level = 'vip'
    def __init__(self, period=14, lower=30, upper=70, **kwargs):
        super().__init__(period=period, lower=lower, upper=upper, **kwargs)
        self.period = int(period)
        self.lower = float(lower)
        self.upper = float(upper)

    def compute_rsi(self, series):
        delta = series.diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ma_up = up.ewm(com=self.period-1, adjust=False).mean()
        ma_down = down.ewm(com=self.period-1, adjust=False).mean()
        rs = ma_up / ma_down
        return 100 - (100 / (1 + rs))

    def generate_signals(self, history):
        import pandas as pd

        df = history.copy()
        df['rsi'] = self.compute_rsi(df['close'])
        df['rsi_shift'] = df['rsi'].shift(1)

        signals = []
        for idx, row in df.iterrows():
            if row['rsi_shift'] <= self.lower and row['rsi'] > self.lower:
                signals.append({'index': idx, 'action': 'buy'})
            elif row['rsi_shift'] >= self.upper and row['rsi'] < self.upper:
                signals.append({'index': idx, 'action': 'sell'})
        return signals

    def backtest(self, history):
        from ..engine import simulate_from_signals
        signals = self.generate_signals(history)
        return simulate_from_signals(history, signals)

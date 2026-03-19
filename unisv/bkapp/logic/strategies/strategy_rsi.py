import pandas as pd
from .base import StrategyBase


class RsiStrategy(StrategyBase):
    """
    日K RSI(6) 超卖策略

    ┌─ 信号 ──────────────────────────────────────────────────┐
    │  买入：RSI(6) < 20                                       │
    │  卖出：价格从持仓后最高价回撤 ≥ 10%                        │
    └─────────────────────────────────────────────────────────┘
    ┌─ 止损 ──────────────────────────────────────────────────┐
    │  硬止损：买入价 × (1 - 10%)                              │
    └─────────────────────────────────────────────────────────┘
    """

    value = '002'
    name  = 'RSI'
    level = 'normal'
    ktype = 'd'
    params = []

    main_indicator = None
    sub_indicator  = {"type": "RSI", "params": {"period": 6}}

    RSI_PERIOD    = 6
    BUY_LEVEL     = 20
    TRAIL_PCT     = 0.10
    HARD_STOP_PCT = 0.10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.total_parts = 10
        self.lookback    = self.RSI_PERIOD + 1

    def prepare(self, df):
        delta = df['close'].diff()
        up    = delta.clip(lower=0)
        down  = -delta.clip(upper=0)
        au    = up.ewm(alpha=1 / self.RSI_PERIOD, adjust=False).mean()
        ad    = down.ewm(alpha=1 / self.RSI_PERIOD, adjust=False).mean()
        rs    = au / ad.replace(0, float('inf'))
        df['rsi'] = 100 - 100 / (1 + rs)

    def backtest(self, history):
        df         = pd.DataFrame(history, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['date'])
        self.prepare(df)

        peak = 0.0  # 持仓后的最高价

        for i in range(self.lookback, len(df)):
            row      = df.iloc[i]
            date_str = row['date'].strftime('%Y/%m/%d')
            close    = float(row['close'])
            rsi      = float(row['rsi'])

            open_records = [r for r in self.history_list if r['sellDate'] == '']

            if open_records:
                peak = max(peak, close)
                buy_price = open_records[0]['buyPrice']

                # 硬止损
                if close <= buy_price * (1 - self.HARD_STOP_PCT):
                    self._sell_all(date_str, close, open_records, '止损')
                    peak = 0.0
                    continue

                # 移动止盈：从最高点回撤 10%
                if close <= peak * (1 - self.TRAIL_PCT):
                    self._sell_all(date_str, close, open_records, '回撤卖出')
                    peak = 0.0
                    continue

            else:
                if rsi < self.BUY_LEVEL:
                    self._buy_all(date_str, close)
                    peak = close

        # 期末未平仓位
        last_close = float(df.iloc[-1]['close'])
        for r in self.history_list:
            if r['sellDate'] == '':
                profit = (last_close - r['buyPrice']) / r['buyPrice']
                r['profitMargin']  = format(profit, '.4f')
                self.total_profit += profit * (r.get('parts', 1) / self.total_parts)

        self.history_list.append({
            'buyDate':           '',
            'buyPrice':          '',
            'sellDate':          '',
            'sellPrice':         '',
            'warehousePosition': round(self.position_parts / self.total_parts, 2),
            'profitMargin':      format(self.total_profit, '.4f'),
        })

        return {
            'code':    0,
            'message': 'success',
            'data': {
                'historyList': self.history_list,
                'markPoint':   {'data': self.mark_points},
            }
        }

    def _buy_all(self, date_str, price):
        parts = self.total_parts
        self.position_parts += parts
        self.history_list.append({
            'buyDate':           date_str,
            'buyPrice':          price,
            'parts':             parts,
            'sellDate':          '',
            'sellPrice':         '',
            'warehousePosition': round(self.position_parts / self.total_parts, 2),
            'profitMargin':      '',
        })
        self.mark_points.append({
            'name':       '买入',
            'coord':      [date_str, price],
            'value':      price,
            'itemStyle':  {'color': '#00AA00'},
            'symbolSize': 30,
        })

    def _sell_all(self, date_str, price, open_records, label='卖出'):
        parts_sold = 0
        for record in open_records:
            profit  = (price - record['buyPrice']) / record['buyPrice']
            parts   = record.get('parts', 1)
            record['sellDate']     = date_str
            record['sellPrice']    = price
            record['profitMargin'] = format(profit, '.4f')
            self.total_profit     += profit * (parts / self.total_parts)
            parts_sold            += parts
        self.position_parts -= parts_sold
        self.mark_points.append({
            'name':       label,
            'coord':      [date_str, price],
            'value':      price,
            'itemStyle':  {'color': '#FF0000'},
            'symbolSize': 40,
        })

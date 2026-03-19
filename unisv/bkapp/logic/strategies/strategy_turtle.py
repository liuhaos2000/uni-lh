import pandas as pd
from .base import StrategyBase


class TurtleMainTrendStrategy(StrategyBase):
    """
    海龟交易法则（主升浪用）

    ┌─ 信号层 ────────────────────────────────────────────────┐
    │  买入：收盘价突破 20 日最高价（唐奇安通道突破）            │
    │  卖出：收盘价跌破 10 日最低价                             │
    └─────────────────────────────────────────────────────────┘
    ┌─ 仓位层（ATR 动态单位 + 金字塔加仓） ──────────────────────┐
    │  单位大小 = 1% 风险 / (2 × ATR/价格)，上限 3 份           │
    │  每上涨 0.5 × ATR，追加 1 单位，最多 4 单位               │
    └─────────────────────────────────────────────────────────┘
    ┌─ 止损层 ────────────────────────────────────────────────┐
    │  任一单位：收盘价 ≤ 该单位入场价 - 2 × ATR → 全部出场     │
    └─────────────────────────────────────────────────────────┘
    """

    value = '006'
    name  = '海龟（主升浪用）'
    level = 'normal'
    params = []

    main_indicator = {"type": "MA", "params": [20]}
    sub_indicator  = None

    # ── 唐奇安通道参数 ────────────────────────────────────────
    ENTRY_PERIOD = 20   # 突破 20 日最高价买入
    EXIT_PERIOD  = 20   # 跌破 20 日最低价卖出

    # ── ATR 参数 ──────────────────────────────────────────────
    ATR_PERIOD = 20
    ATR_MULT   = 2.0    # 止损距离 = 2 × N

    # ── 金字塔参数 ────────────────────────────────────────────
    ADD_N_MULT = 0.5    # 每上涨 0.5N 追加 1 单位
    MAX_UNITS  = 4      # 最多持有 4 个单位

    # ── 风险控制 ──────────────────────────────────────────────
    RISK_PER_UNIT = 0.01   # 每单位最大风险 = 总资金的 1%

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.total_parts = 10
        self.lookback    = self.ENTRY_PERIOD + self.ATR_PERIOD

    # ── 指标计算 ──────────────────────────────────────────────

    def prepare(self, df):
        # 唐奇安通道（shift(1) 避免用当天数据，防止未来函数）
        df['high20'] = df['high'].rolling(self.ENTRY_PERIOD).max().shift(1)
        df['low10']  = df['low'].rolling(self.EXIT_PERIOD).min().shift(1)

        # ATR
        hl        = df['high'] - df['low']
        hpc       = (df['high'] - df['close'].shift()).abs()
        lpc       = (df['low']  - df['close'].shift()).abs()
        tr        = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
        df['atr'] = tr.rolling(self.ATR_PERIOD).mean()

    # ── 信号 ──────────────────────────────────────────────────

    def generate_buy_signal(self, df, i):
        curr = df.iloc[i]
        if pd.isna(curr['high20']):
            return False
        return float(curr['close']) > float(curr['high20'])

    def generate_sell_signal(self, df, i):
        curr = df.iloc[i]
        if pd.isna(curr['low10']):
            return False
        return float(curr['close']) < float(curr['low10'])

    # ── ATR 动态仓位计算 ──────────────────────────────────────

    def _calc_unit_parts(self, close, atr):
        """
        根据 ATR 计算本次买入的份数。
        波动越大 → 份数越少；波动越小 → 份数越多（上限 3 份）。
        """
        if atr <= 0 or close <= 0:
            return 2
        atr_pct = atr / close
        # 每单位风险 = 1%；止损距离 = 2 × atr_pct
        unit_pct = self.RISK_PER_UNIT / (2 * atr_pct)
        parts    = round(unit_pct * self.total_parts)
        return max(1, min(3, parts))

    # ── 回测主流程 ────────────────────────────────────────────

    def backtest(self, history):
        df         = pd.DataFrame(history, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['date'])
        self.prepare(df)

        # units: 每个单位记录 {entry_price, stop, parts}
        units      = []
        unit_count = 0
        last_entry = 0.0   # 最近一次建仓/加仓的价格

        for i in range(self.lookback, len(df)):
            row      = df.iloc[i]
            date_str = row['date'].strftime('%Y/%m/%d')
            close    = float(row['close'])
            atr      = float(row['atr']) if pd.notna(row['atr']) else 0.0

            open_records = [r for r in self.history_list if r['sellDate'] == '']

            # ── 有持仓：先检查出场 ────────────────────────────
            if open_records:

                # ① ATR 止损：任一单位的止损价被触穿 → 全部出场
                if atr > 0 and any(close <= u['stop'] for u in units):
                    self._sell_all(date_str, close, open_records)
                    units = []; unit_count = 0; last_entry = 0.0
                    continue

                # ② 通道出场：跌破 10 日最低价
                if self.generate_sell_signal(df, i):
                    self._sell_all(date_str, close, open_records)
                    units = []; unit_count = 0; last_entry = 0.0
                    continue

                # ── 金字塔加仓：每上涨 0.5N 追加一单位 ──────
                if unit_count < self.MAX_UNITS and atr > 0:
                    add_trigger = last_entry + self.ADD_N_MULT * atr
                    if close >= add_trigger:
                        parts = self._calc_unit_parts(close, atr)
                        if self.position_parts + parts <= self.total_parts:
                            stop = close - self.ATR_MULT * atr
                            units.append({'entry_price': close, 'stop': stop, 'parts': parts})
                            unit_count += 1
                            last_entry  = close
                            self._buy_parts(date_str, close, parts)
                continue   # 持仓期间不检查初次买入

            # ── 空仓：突破 20 日高点买入 ─────────────────────
            if self.generate_buy_signal(df, i) and atr > 0:
                parts = self._calc_unit_parts(close, atr)
                stop  = close - self.ATR_MULT * atr
                units.append({'entry_price': close, 'stop': stop, 'parts': parts})
                unit_count = 1
                last_entry = close
                self._buy_parts(date_str, close, parts)

        # ── 期末未平仓位 ──────────────────────────────────────
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

    # ── 辅助方法 ──────────────────────────────────────────────

    def _buy_parts(self, date_str, price, parts):
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
            'name':       f'买{parts * 10}%',
            'coord':      [date_str, price],
            'value':      price,
            'itemStyle':  {'color': '#00AA00'},
            'symbolSize': 20 + parts * 4,
        })

    def _sell_all(self, date_str, price, open_records):
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
            'name':       '卖出',
            'coord':      [date_str, price],
            'value':      price,
            'itemStyle':  {'color': '#FF0000'},
            'symbolSize': 40,
        })

import pandas as pd
from .base import StrategyBase


class RollingStrategy(StrategyBase):
    """
    滚仓策略（底仓长线 + 滚仓短线）

    ┌─ 底仓（30%，长线）────────────────────────────────────────┐
    │  买入：RSI(6)<35 + RSI(14)>45 + MA20>MA60               │
    │  退出：MA20下穿MA60 / 全局止损-8%                         │
    └──────────────────────────────────────────────────────────┘
    ┌─ 滚仓（20%/单位，最多2单位，短线）────────────────────────┐
    │  前提：底仓浮盈曾≥10% 且 当前底仓仍有盈利                  │
    │  买入：单日跌幅 ≥ 3%                                     │
    │  卖出1单位（FIFO）：单日涨幅 ≥ 3%                         │
    │  卖出全部：单日涨幅 ≥ 5%                                  │
    │  单笔止损：该笔亏损 ≤ -5%                                 │
    └──────────────────────────────────────────────────────────┘
    ┌─ 全局止损──────────────────────────────────────────────────┐
    │  整体平均成本跌 -8%  → 底仓 + 所有滚仓全清                  │
    │  MA20 下穿 MA60     → 底仓 + 所有滚仓全清                  │
    └──────────────────────────────────────────────────────────┘
    """

    value  = '007'
    name   = '滚仓'
    level  = 'normal'
    params = []

    main_indicator = {"type": "MA",  "params": [20, 60]}
    sub_indicator  = {"type": "RSI", "params": {"period": 6}}

    # ── RSI 参数 ──────────────────────────────────────────────
    RSI_SHORT = 6
    RSI_LONG  = 14
    BUY_RSI   = 35    # 短 RSI 建底仓阈值
    TREND_RSI = 45    # 长 RSI 趋势过滤

    # ── 均线 ──────────────────────────────────────────────────
    MA_SHORT = 20
    MA_LONG  = 60

    # ── 仓位 ──────────────────────────────────────────────────
    BASE_PARTS    = 3   # 底仓 30%
    ROLLING_PARTS = 2   # 滚仓每单位 20%
    MAX_ROLLING   = 2   # 最多同时持有 2 单位滚仓

    # ── 滚仓触发 ──────────────────────────────────────────────
    BASE_PROFIT_MIN = 0.10   # 底仓浮盈首次达到此值后开放滚仓
    ROLL_BUY_DROP   = 0.03   # 单日跌幅 ≥ 3% → 买 1 单位滚仓
    ROLL_SELL_ONE   = 0.03   # 单日涨幅 ≥ 3% → 卖 1 单位滚仓（FIFO）
    ROLL_SELL_ALL   = 0.05   # 单日涨幅 ≥ 5% → 卖全部滚仓

    # ── 止损 ──────────────────────────────────────────────────
    ROLLING_STOP_PCT = 0.05   # 滚仓单笔止损 -5%
    GLOBAL_STOP_PCT  = 0.08   # 全局止损 -8%

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.total_parts = 10
        self.lookback    = self.MA_LONG + self.RSI_LONG

    # ── 指标计算 ──────────────────────────────────────────────

    def prepare(self, df):
        df['rsi_short'] = self._calc_rsi(df['close'], self.RSI_SHORT)
        df['rsi_long']  = self._calc_rsi(df['close'], self.RSI_LONG)
        df['ma_short']  = df['close'].rolling(self.MA_SHORT).mean()
        df['ma_long']   = df['close'].rolling(self.MA_LONG).mean()
        df['daily_ret'] = df['close'].pct_change()

    def _calc_rsi(self, series, period):
        delta = series.diff()
        up    = delta.clip(lower=0)
        down  = -delta.clip(upper=0)
        au    = up.ewm(alpha=1 / period, adjust=False).mean()
        ad    = down.ewm(alpha=1 / period, adjust=False).mean()
        rs    = au / ad.replace(0, float('inf'))
        return 100 - 100 / (1 + rs)

    # ── 信号判断 ──────────────────────────────────────────────

    def _base_buy_signal(self, row):
        if pd.isna(row['ma_long']):
            return False
        return (float(row['rsi_short']) < self.BUY_RSI and
                float(row['rsi_long'])  > self.TREND_RSI and
                float(row['ma_short'])  > float(row['ma_long']))

    def _ma_death_cross(self, df, i):
        prev, curr = df.iloc[i - 1], df.iloc[i]
        if pd.isna(curr['ma_long']) or pd.isna(prev['ma_long']):
            return False
        return (float(prev['ma_short']) >= float(prev['ma_long']) and
                float(curr['ma_short'])  <  float(curr['ma_long']))

    # ── 回测主流程 ────────────────────────────────────────────

    def backtest(self, history):
        df         = pd.DataFrame(history, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['date'])
        self.prepare(df)

        base_record          = None   # 当前底仓记录
        rolling_records      = []     # 当前活跃滚仓列表（FIFO 顺序）
        rolling_ever_reached = False  # 底仓浮盈是否曾达到 10%

        for i in range(self.lookback, len(df)):
            row       = df.iloc[i]
            date_str  = row['date'].strftime('%Y/%m/%d')
            close     = float(row['close'])
            daily_ret = float(row['daily_ret']) if pd.notna(row['daily_ret']) else 0.0

            # ── 当前状态 ──────────────────────────────────────
            has_base = base_record is not None and base_record['sellDate'] == ''
            base_profit = ((close - base_record['buyPrice']) / base_record['buyPrice']
                           if has_base else 0.0)

            if has_base and base_profit >= self.BASE_PROFIT_MIN:
                rolling_ever_reached = True

            # ── 全局出场：止损 / MA 死叉 ──────────────────────
            if has_base or rolling_records:
                all_open = [r for r in self.history_list if r['sellDate'] == '']

                # 全局止损
                if all_open:
                    tp = sum(r.get('parts', 1) for r in all_open)
                    avg_cost = sum(r['buyPrice'] * r.get('parts', 1) for r in all_open) / tp
                    if close <= avg_cost * (1 - self.GLOBAL_STOP_PCT):
                        self._sell_all(date_str, close, all_open, label='止损清仓')
                        base_record = None
                        rolling_records = []
                        rolling_ever_reached = False
                        continue

                # MA 死叉
                if self._ma_death_cross(df, i):
                    all_open = [r for r in self.history_list if r['sellDate'] == '']
                    self._sell_all(date_str, close, all_open, label='趋势清仓')
                    base_record = None
                    rolling_records = []
                    rolling_ever_reached = False
                    continue

            # ── 滚仓管理 ──────────────────────────────────────
            if rolling_records:
                # ① 单笔止损 -5%
                to_stop = [r for r in rolling_records
                           if (close - r['buyPrice']) / r['buyPrice'] <= -self.ROLLING_STOP_PCT]
                for r in to_stop:
                    self._sell_single(date_str, close, r, label='滚仓止损')
                    rolling_records.remove(r)

                # ② 单日涨幅 ≥ 5%：卖出所有滚仓
                if daily_ret >= self.ROLL_SELL_ALL and rolling_records:
                    for r in list(rolling_records):
                        self._sell_single(date_str, close, r, label='卖滚仓')
                    rolling_records.clear()

                # ③ 单日涨幅 ≥ 3%：卖出最早一笔（FIFO）
                elif daily_ret >= self.ROLL_SELL_ONE and rolling_records:
                    oldest = rolling_records.pop(0)
                    self._sell_single(date_str, close, oldest, label='卖滚仓')

            # ── 滚仓买入 ──────────────────────────────────────
            rolling_ok = (rolling_ever_reached and
                          has_base and
                          base_profit > 0 and
                          len(rolling_records) < self.MAX_ROLLING)

            if rolling_ok and daily_ret <= -self.ROLL_BUY_DROP:
                if self.position_parts + self.ROLLING_PARTS <= self.total_parts:
                    rec = self._buy_parts(date_str, close, self.ROLLING_PARTS, 'rolling')
                    rolling_records.append(rec)

            # ── 底仓买入（空仓时） ─────────────────────────────
            if not has_base and self._base_buy_signal(row):
                if self.position_parts + self.BASE_PARTS <= self.total_parts:
                    base_record = self._buy_parts(date_str, close, self.BASE_PARTS, 'base')
                    rolling_ever_reached = False   # 新底仓，重置滚仓权限

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

    def _buy_parts(self, date_str, price, parts, record_type):
        self.position_parts += parts
        record = {
            'buyDate':           date_str,
            'buyPrice':          price,
            'parts':             parts,
            'type':              record_type,
            'sellDate':          '',
            'sellPrice':         '',
            'warehousePosition': round(self.position_parts / self.total_parts, 2),
            'profitMargin':      '',
        }
        self.history_list.append(record)
        self.mark_points.append({
            'name':       '底仓30%' if record_type == 'base' else '滚仓20%',
            'coord':      [date_str, price],
            'value':      price,
            'itemStyle':  {'color': '#005500' if record_type == 'base' else '#00AA00'},
            'symbolSize': 32 if record_type == 'base' else 22,
        })
        return record

    def _sell_single(self, date_str, price, record, label='卖出'):
        profit = (price - record['buyPrice']) / record['buyPrice']
        parts  = record.get('parts', 1)
        record['sellDate']     = date_str
        record['sellPrice']    = price
        record['profitMargin'] = format(profit, '.4f')
        self.total_profit     += profit * (parts / self.total_parts)
        self.position_parts   -= parts
        self.mark_points.append({
            'name':       label,
            'coord':      [date_str, price],
            'value':      price,
            'itemStyle':  {'color': '#FF6600'},
            'symbolSize': 22,
        })

    def _sell_all(self, date_str, price, open_records, label='清仓'):
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

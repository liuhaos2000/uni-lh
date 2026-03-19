import pandas as pd
from .base import StrategyBase


class MACDTrendStrategy(StrategyBase):
    """
    MACD 趋势跟踪策略（含完整仓位管理）

    ┌─ 信号层 ────────────────────────────────────────────┐
    │  买入：MACD 金叉 + 收盘价站上 MA20（趋势过滤）        │
    │  卖出：MACD 死叉                                    │
    └─────────────────────────────────────────────────────┘
    ┌─ 仓位层（金字塔加仓） ───────────────────────────────┐
    │  第1档：金叉当日            → 建仓 40%              │
    │  第2档：持仓中回踩 MA20     → 加仓 30%              │
    │  第3档：持仓中再次回踩 MA20 → 加仓 20%              │
    │  最大仓位 90%，保留 10% 现金缓冲                     │
    │  每次加仓间隔至少 5 个交易日（冷却期）                │
    └─────────────────────────────────────────────────────┘
    ┌─ 止损层（二级保护，取较近者） ──────────────────────┐
    │  硬止损：平均成本 × (1 - 8%)                        │
    │  ATR止损：平均成本 - 2 × ATR(20)                    │
    └─────────────────────────────────────────────────────┘
    ┌─ 止盈层（移动止盈） ─────────────────────────────────┐
    │  浮盈 ≥ 10% 时启动                                  │
    │  价格从最高点回撤 ≥ 8% 时全部出场                    │
    └─────────────────────────────────────────────────────┘
    """

    value       = '005'
    name        = 'MACD_Trend'
    level       = 'normal'
    params      = []
    title       = 'MACD趋势跟踪'
    description = 'MACD金叉建仓 + MA20回踩加仓 + ATR止损 + 移动止盈'

    main_indicator = {"type": "MA",   "params": [5, 20]}
    sub_indicator  = {"type": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}}

    # ── MACD 参数 ──────────────────────────────────────
    MACD_FAST   = 12
    MACD_SLOW   = 26
    MACD_SIGNAL = 9

    # ── 趋势过滤 ────────────────────────────────────────
    TREND_MA = 20

    # ── 金字塔仓位（总 10 份） ───────────────────────────
    # 第1档金叉建仓，第2/3档回踩MA20加仓
    PYRAMID   = [4, 3, 2]   # 40% / 30% / 20%
    MAX_PARTS = 9            # 最大仓位 90%

    # 回踩 MA20 的判定范围：收盘价在 MA20 的 [-1%, +2%] 区间内
    MA20_TOUCH_LOW  = 0.99
    MA20_TOUCH_HIGH = 1.02

    # 每次加仓的最短间隔（交易日）
    ADD_COOLDOWN = 5

    # ── 止损 ────────────────────────────────────────────
    HARD_STOP_PCT = 0.08
    ATR_PERIOD    = 20
    ATR_MULT      = 2.0

    # ── 移动止盈 ─────────────────────────────────────────
    TRAIL_TRIGGER  = 0.10
    TRAIL_STOP_PCT = 0.08

    # ---------------------------------------------------

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.total_parts = 10
        self.lookback    = self.MACD_SLOW + self.MACD_SIGNAL

    # ── 指标计算 ─────────────────────────────────────────

    def prepare(self, df):
        # MACD
        ema_f     = df['close'].ewm(span=self.MACD_FAST,   adjust=False).mean()
        ema_s     = df['close'].ewm(span=self.MACD_SLOW,   adjust=False).mean()
        df['dif'] = ema_f - ema_s
        df['dea'] = df['dif'].ewm(span=self.MACD_SIGNAL, adjust=False).mean()

        # MA20
        df['ma20'] = df['close'].rolling(self.TREND_MA).mean()

        # ATR
        hl        = df['high'] - df['low']
        hpc       = (df['high'] - df['close'].shift()).abs()
        lpc       = (df['low']  - df['close'].shift()).abs()
        tr        = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
        df['atr'] = tr.rolling(self.ATR_PERIOD).mean()

        # 成交量比（当日量 / 20日均量）
        if 'volume' in df.columns:
            df['vol_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        else:
            df['vol_ratio'] = 1.0   # 无量数据时不过滤

    # ── 买入信号：金叉 + 站上 MA20 ───────────────────────

    def generate_buy_signal(self, df, i):
        prev, curr   = df.iloc[i - 1], df.iloc[i]
        golden_cross = (prev['dif'] <= prev['dea']) and (curr['dif'] > curr['dea'])
        above_ma20   = curr['close'] > curr['ma20']
        above_zero   = curr['dif'] > 0          # 零轴过滤：只做上升趋势中的金叉
        vol_confirm  = curr['vol_ratio'] >= 1.0  # 成交量过滤：不低于均量
        return golden_cross and above_ma20 and above_zero and vol_confirm

    # ── 卖出信号：死叉 ───────────────────────────────────

    def generate_sell_signal(self, df, i):
        prev, curr = df.iloc[i - 1], df.iloc[i]
        return (prev['dif'] >= prev['dea']) and (curr['dif'] < curr['dea'])

    # ── 加仓信号：回踩 MA20（持仓中，DIF 仍 > DEA）────────

    def _is_pullback_buy(self, df, i):
        """
        持仓中的回踩加仓条件：
          1. 价格在 MA20 附近（±1~2%）
          2. DIF > DEA（MACD 仍偏多，未死叉）
        """
        curr  = df.iloc[i]
        close = float(curr['close'])
        ma20  = float(curr['ma20'])
        if pd.isna(ma20) or ma20 == 0:
            return False
        near_ma20     = self.MA20_TOUCH_LOW <= (close / ma20) <= self.MA20_TOUCH_HIGH
        macd_positive = float(curr['dif']) > float(curr['dea'])
        return near_ma20 and macd_positive

    # ── 回测主流程 ────────────────────────────────────────

    def backtest(self, history):
        df         = pd.DataFrame(history, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['date'])
        self.prepare(df)

        buy_count       = 0     # 已买入次数（决定金字塔档位）
        last_buy_idx    = -999  # 上次买入的行索引（用于冷却期判断）
        peak_price      = 0.0
        trailing_active = False

        for i in range(self.lookback, len(df)):
            row      = df.iloc[i]
            date_str = row['date'].strftime('%Y/%m/%d')
            close    = float(row['close'])
            atr      = float(row['atr']) if pd.notna(row['atr']) else 0.0

            open_records = [r for r in self.history_list if r['sellDate'] == '']

            # ── 有持仓：检查所有出场条件 ─────────────────────
            if open_records:
                peak_price = max(peak_price, close)

                total_parts_held = sum(r.get('parts', 1) for r in open_records)
                avg_cost         = sum(r['buyPrice'] * r.get('parts', 1) for r in open_records) / total_parts_held
                floating_profit = (close - avg_cost) / avg_cost

                if floating_profit >= self.TRAIL_TRIGGER:
                    trailing_active = True

                exit_reason = None

                # ① 移动止盈
                if trailing_active and close <= peak_price * (1 - self.TRAIL_STOP_PCT):
                    exit_reason = 'trailing_stop'

                # ② 综合止损
                if exit_reason is None:
                    hard_stop  = avg_cost * (1 - self.HARD_STOP_PCT)
                    atr_stop   = (avg_cost - self.ATR_MULT * atr) if atr > 0 else hard_stop
                    stop_level = min(hard_stop, atr_stop)  # 取较宽一侧，减少噪音震出
                    if close <= stop_level:
                        exit_reason = 'stop_loss'

                # ③ MACD 死叉
                if exit_reason is None and self.generate_sell_signal(df, i):
                    exit_reason = 'death_cross'

                if exit_reason:
                    self._sell_all(date_str, close, open_records)
                    buy_count       = 0
                    last_buy_idx    = -999
                    peak_price      = 0.0
                    trailing_active = False
                    continue

                # ── 持仓中：检查回踩 MA20 加仓 ───────────────
                cooldown_ok = (i - last_buy_idx) >= self.ADD_COOLDOWN
                can_add     = buy_count < len(self.PYRAMID) and cooldown_ok

                if can_add and buy_count > 0 and self._is_pullback_buy(df, i):
                    parts = self.PYRAMID[buy_count]
                    if self.position_parts + parts <= self.MAX_PARTS:
                        self._buy_parts(date_str, close, parts)
                        buy_count    += 1
                        last_buy_idx  = i
                    continue

            # ── 空仓：检查金叉买入 ────────────────────────────
            if not open_records and self.generate_buy_signal(df, i):
                parts = self.PYRAMID[0]   # 第一档：40%
                self._buy_parts(date_str, close, parts)
                buy_count    = 1
                last_buy_idx = i
                peak_price   = close

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

    # ── 辅助方法 ──────────────────────────────────────────

    def _buy_parts(self, date_str, price, parts):
        self.position_parts += parts
        pct = parts * 10
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
            'name':      f'买{pct}%',
            'coord':     [date_str, price],
            'value':     price,
            'itemStyle': {'color': '#00AA00'},
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
            'name':      '卖出',
            'coord':     [date_str, price],
            'value':     price,
            'itemStyle': {'color': '#FF0000'},
            'symbolSize': 40,
        })

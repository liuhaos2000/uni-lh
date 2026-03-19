import pandas as pd
from typing import Optional


def calculate_indicators(df: pd.DataFrame,
                         main_config: Optional[dict],
                         sub_config: Optional[dict]) -> dict:
    """
    根据策略声明的 main_indicator / sub_indicator 配置，计算指标数据。
    返回格式供前端 ECharts 直接使用。
    """
    return {
        'mainIndicator': _calc_main(df, main_config) if main_config else None,
        'subIndicator':  _calc_sub(df, sub_config)  if sub_config  else None,
    }


# ---------- 工具函数 ----------

def _fmt(series: pd.Series) -> list:
    """将 pandas Series 转成 JSON 可序列化的列表，NaN → None"""
    return [round(float(v), 4) if pd.notna(v) else None for v in series]


# ---------- 主图指标 ----------

def _calc_main(df: pd.DataFrame, config: dict) -> Optional[dict]:
    t      = config.get('type', 'MA')
    params = config.get('params', [5, 10, 20])

    if t == 'MA':
        return {
            'type': 'MA',
            'series': [
                {'name': f'MA{p}', 'data': _fmt(df['close'].rolling(p).mean())}
                for p in params
            ]
        }

    if t == 'EMA':
        return {
            'type': 'EMA',
            'series': [
                {'name': f'EMA{p}',
                 'data': _fmt(df['close'].ewm(span=p, adjust=False).mean())}
                for p in params
            ]
        }

    if t == 'BOLL':
        p     = params.get('period', 20) if isinstance(params, dict) else 20
        std_m = params.get('std',    2)  if isinstance(params, dict) else 2
        mid   = df['close'].rolling(p).mean()
        std   = df['close'].rolling(p).std()
        return {
            'type': 'BOLL',
            'series': [
                {'name': 'UPPER', 'data': _fmt(mid + std_m * std)},
                {'name': 'MID',   'data': _fmt(mid)},
                {'name': 'LOWER', 'data': _fmt(mid - std_m * std)},
            ]
        }

    return None


# ---------- 附图指标 ----------

def _calc_sub(df: pd.DataFrame, config: dict) -> Optional[dict]:
    t      = config.get('type')
    params = config.get('params', {})
    if not isinstance(params, dict):
        params = {}

    if t == 'RSI':
        period = params.get('period', 14)
        delta  = df['close'].diff()
        au     = delta.clip(lower=0).ewm(com=period - 1, adjust=False).mean()
        ad     = (-delta.clip(upper=0)).ewm(com=period - 1, adjust=False).mean()
        rsi    = 100 - 100 / (1 + au / ad)
        return {
            'type': 'RSI',
            'series': [
                {'name': f'RSI{period}', 'data': _fmt(rsi)}
            ]
        }

    if t == 'MACD':
        fast   = params.get('fast',   12)
        slow   = params.get('slow',   26)
        signal = params.get('signal',  9)
        ema_f  = df['close'].ewm(span=fast,   adjust=False).mean()
        ema_s  = df['close'].ewm(span=slow,   adjust=False).mean()
        dif    = ema_f - ema_s
        dea    = dif.ewm(span=signal, adjust=False).mean()
        hist   = 2 * (dif - dea)
        return {
            'type': 'MACD',
            'series': [
                {'name': 'DIF',  'data': _fmt(dif)},
                {'name': 'DEA',  'data': _fmt(dea)},
                {'name': 'MACD', 'data': _fmt(hist)},
            ]
        }

    if t == 'KDJ':
        n  = params.get('n',  9)
        m1 = params.get('m1', 3)
        m2 = params.get('m2', 3)
        low_min  = df['low'].rolling(n).min()
        high_max = df['high'].rolling(n).max()
        rsv = (df['close'] - low_min) / (high_max - low_min) * 100
        K   = rsv.ewm(com=m1 - 1, adjust=False).mean()
        D   = K.ewm(com=m2 - 1,   adjust=False).mean()
        J   = 3 * K - 2 * D
        return {
            'type': 'KDJ',
            'series': [
                {'name': 'K', 'data': _fmt(K)},
                {'name': 'D', 'data': _fmt(D)},
                {'name': 'J', 'data': _fmt(J)},
            ]
        }

    return None

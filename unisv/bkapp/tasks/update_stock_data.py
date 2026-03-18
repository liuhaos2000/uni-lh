from celery import shared_task
import akshare as ak
from django.utils import timezone
from datetime import time
from django.core.cache import cache

def is_trade_time(now):
    """判斷是否為 A 股交易時間"""
    t = now.time()

    # 早市 09:30-11:30
    if time(9, 30) <= t <= time(11, 30):
        return True

    # 午市 13:00-15:00
    if time(13, 0) <= t <= time(15, 0):
        return True

    return False


last_run_minute = None   # 全局記憶最近執行的 minute
last_run_15min = None    # 全局記憶最近的 15 分鐘


@shared_task
def update_stock_data():
    """
    交易時段：每 1 分鐘執行
    非交易時段：每 15 分鐘執行
    """
    global last_run_minute, last_run_15min

    now = timezone.localtime()
    # 先检查缓存中是否有数据
    stock_data = cache.get('stock_data')
    if stock_data is None:
        do_fetch_stock()
        return "缓存中无数据，已抓取并更新缓存"
        
    if is_trade_time(now):
        if last_run_minute == now.minute:
            return "已在本分鐘執行過（交易時間）"

        # === 交易時間：每分鐘抓取 ===
        do_fetch_stock()
        last_run_minute = now.minute
        return "交易時間：已抓取"
    else:
        # 非交易時間：每 15 分鐘抓一次（00/15/30/45）
        if now.minute % 15 != 0:
            return "非交易時間但未到 15 分鐘點"

        if last_run_15min == now.minute:
            return "非交易時間：本 15 分鐘已執行過"

        do_fetch_stock()
        last_run_15min = now.minute
        return "非交易時間：已按 15 分鐘抓取"



def do_fetch_stock():
    """真正抓取 AkShare 數據的函數"""
    try:
        df = ak.stock_zh_a_spot_em()
        stock_data = df.to_dict(orient='records')
        cache.set('stock_data', stock_data, 60)
    except Exception as e:
        print(f"抓取失敗: {e}")





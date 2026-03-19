from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ..models.watchlists import Watchlist
from ..models.watchlist_stocks import WatchlistStock
from ..global_data import get_allskname_fromapi_global
import pandas as pd
import requests
from datetime import datetime, timedelta
from django.conf import settings
from bkapp.logic.strategies.registry import get_strategy, get_strategy_by_value
from bkapp.logic.indicators.calculator import calculate_indicators

@api_view(['GET'])
def get_sk_k(request):
    try:
        skId = request.query_params.get('skId')

        converted_data = fetch_and_convert_data(skId)

        try:
            allnames = get_allskname_fromapi_global()
            skName = next((item['mc'] for item in allnames if item['dm'][:6] == skId[:6]), skId)
        except Exception:
            skName = skId

        return Response({
            "code": 0,
            "message": "success",
            "data": {
                "title": f"{skName}（{skId}）",
                "raw": converted_data
            }
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            "code": 500,
            "message": f"Error: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_huice(request):
    try:
        skId    = request.query_params.get('skId')
        celueId = request.query_params.get('celueId')

        strategy_class    = get_strategy_by_value(celueId)

        # 获取历史 K 线数据（根据策略的 ktype 选日K或周K）
        ktype   = getattr(strategy_class, 'ktype', 'd')
        history = fetch_and_convert_data(skId, ktype)
        strategy_instance = strategy_class(skId=skId)
        out_data          = strategy_instance.backtest(history)

        # 计算策略对应的主图/附图指标数据
        df = pd.DataFrame(history, columns=["date", "open", "high", "low", "close", "volume"])
        indicators = calculate_indicators(
            df,
            getattr(strategy_class, 'main_indicator', None),
            getattr(strategy_class, 'sub_indicator',  None),
        )
        out_data['data']['indicators'] = indicators

        return Response(out_data)

    except Exception as e:
        return Response({
            "code": 500,
            "message": f"Error: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#获取历史数据
def fetch_and_convert_data(skId, ktype='d'):
    try:
        today = datetime.today()
        endDate = today.strftime('%Y%m%d')
        three_years_ago = today - timedelta(days=365 * 3)
        startDate = three_years_ago.strftime('%Y%m%d')

        url = f"http://api.momaapi.com/hsstock/history/{skId}/{ktype}/n/{settings.MOMA_TOKEN}?st={startDate}&et={endDate}&lt=750"
        response = requests.get(url)
        try:
            data = response.json()
        except Exception:
            raise Exception(f"行情数据接口异常：{response.text[:100]}")
        if isinstance(data, str) or not isinstance(data, list):
            raise Exception(f"行情数据接口返回错误：{str(data)[:100]}")

        converted_data = []

        for item in data:
            # 提取日期并格式化
            date = datetime.strptime(item["t"], "%Y-%m-%d %H:%M:%S").strftime("%Y/%m/%d")
            
            # 提取其他数值
            open_price = item["o"]
            high_price = item["h"]
            low_price = item["l"]
            close_price = item["c"]
            
            # 将数据添加到转换后的列表中
            volume = item.get("v", 0)
            converted_data.append([date, open_price, high_price, low_price, close_price, volume])

        return converted_data

    except Exception as e:
        raise Exception(f"Error fetching and converting data: {str(e)}")



@api_view(['POST'])
def addToWatchlist(request):
    try:
        # 支持从 POST body 或 query params 获取参数
        skId = request.data.get('stock_code') if hasattr(request, 'data') else None
        if not skId:
            skId = request.query_params.get('stock_code')

        openid = "111"

        if not skId:
            return Response({"code": 400, "message": "stock_code is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 查找用户的 watchlist，若不存在则创建一个默认的
        watchlist = Watchlist.objects.filter(openid=openid).first()
        if not watchlist:
            watchlist = Watchlist.objects.create(openid=openid, name='默认')

        # 检查是否已存在该股票
        exists = WatchlistStock.objects.filter(watchlist=watchlist, stock_code=skId).exists()
        if exists:
            return Response({"code": 0, "message": "already_exists", "data": {"stock_code": skId}}, status=status.HTTP_200_OK)

        wstock = WatchlistStock.objects.create(watchlist=watchlist, stock_code=skId)

        return Response({"code": 0, "message": "success", "data": wstock.to_dict()}, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"code": 500, "message": f"Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def removeFromWatchlist(request):
    try:
        skId = request.data.get('stock_code') if hasattr(request, 'data') else None
        if not skId:
            skId = request.query_params.get('stock_code')

        openid = "111"

        if not skId:
            return Response({"code": 400, "message": "stock_code is required"}, status=status.HTTP_400_BAD_REQUEST)

        watchlist = Watchlist.objects.filter(openid=openid).first()
        if not watchlist:
            return Response({"code": 404, "message": "watchlist_not_found"}, status=status.HTTP_404_NOT_FOUND)

        qs = WatchlistStock.objects.filter(watchlist=watchlist, stock_code=skId)
        deleted_count = qs.count()
        if deleted_count == 0:
            return Response({"code": 404, "message": "stock_not_found"}, status=status.HTTP_404_NOT_FOUND)

        qs.delete()

        return Response({"code": 0, "message": "success", "data": {"stock_code": skId, "deleted": deleted_count}}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"code": 500, "message": f"Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
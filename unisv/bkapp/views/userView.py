from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from ..models.watchlists import Watchlist
from ..models.watchlist_stocks import WatchlistStock
import requests
from ..global_data import get_allskname_fromapi_global

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_first_stock(request):
    """Get all stock codes from the first watchlist of a user.
    
    Parameters:
        openid: User's openid (query parameter)
    
    Returns:
        {
            "code": 0
            "message": "success",
            "data": [
                {"stock_code": "AAPL", "added_at": "2025-11-20T10:30:00Z"},
                {"stock_code": "MSFT", "added_at": "2025-11-20T10:35:00Z"}
            ]
        }
    """
    user = request.user
    openid = str(user.id)

    try:
        # 真实用户信息
        user_info = {
            "userName": user.nickname or user.username,
            "userImage": user.headimg or "https://vkceyugu.cdn.bspapp.com/VKCEYUGU-dc-site/094a9dc0-50c0-11eb-b680-7980c8a877b8.jpg",
            "userLevel": "VIP" if user.is_vip else "普通",
            "userLevelTimeLimit": "—",
            "is_vip": user.is_vip,
            "backtest_count": user.backtest_count,
            "backtest_quota": user.backtest_quota,
        }

        # 拿当前用户的 watchlist
        watchlist = Watchlist.objects.filter(openid=openid).first()

        if not watchlist:
            return Response({
                "code": 0,
                "message": "success",
                "data": {**user_info, "userSkList": []}
            }, status=status.HTTP_200_OK)

        stocks = WatchlistStock.objects.filter(watchlist=watchlist)

        if not stocks.exists():
            return Response({
                "code": 0,
                "message": "success",
                "data": {**user_info, "userSkList": []}
            }, status=status.HTTP_200_OK)

        stocks_code = []
        for stock in stocks:
            stocks_code.append({
                "stock_code": stock.stock_code,
                "added_at": stock.added_at.isoformat() if stock.added_at else None
            })

        stocks_data = get_stocks_from_codes(stocks_code)

        return Response({
            "code": 0,
            "message": "success",
            "data": {**user_info, "userSkList": stocks_data}
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            "code": 500,
            "message": f"Error: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





def get_stocks_from_codes(stock_codes):

    codes = ",".join(code["stock_code"] for code in stock_codes)

    stock_data = []

    url = f"http://api.momaapi.com/hsrl/ssjy_more/{settings.MOMA_TOKEN}?stock_codes={codes}"; 

    response = requests.get(url)

    if response.status_code == 200:
        all_stock_info = response.json()
    else:
        print(f"请求失败，状态码: {response.status_code}")

    allnames = get_allskname_fromapi_global()

    for code_dict in stock_codes:
        code = code_dict['stock_code']
        name = next((item['mc'] for item in allnames if item['dm'][:6] == code[:6]), None)
        try:
            # 从获取的所有股票数据中筛选目标股票
            stock_row = next((item for item in all_stock_info if item['dm'] == code), None)

            if stock_row is not None:
                stock_data.append({
                    "skId": code,
                    "skName": name,
                    "price": stock_row['p'] ,  # 处理 NaN
                    "movement": stock_row['pc']   # 处理 NaN
                })
            else:
                print(f"Stock code {code} not found in all_stock_info")
        except Exception as e:
            print(f"Error processing data for {code}: {e}")

    return stock_data


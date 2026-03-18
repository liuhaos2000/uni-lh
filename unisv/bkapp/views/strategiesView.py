from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..logic.strategies.registry import strategy_registry
from ..models.watchlists import Watchlist
from ..models.watchlist_stocks import WatchlistStock

@api_view(['GET'])
#@permission_classes([IsAuthenticated])  # 需要登录
def list_strategies(request):
    user = request.user
    is_vip = getattr(user, 'is_vip', False)

    strategies = []

    for name, cls in strategy_registry.items():
        # VIP 策略过滤
        if getattr(cls, "level", "normal") == "vip" and not is_vip:
            continue

        # 参数格式： [{"name": "period", "type": "int", "default": 10}]
        # 支持两种格式：字符串列表 ['period', 'lower'] 或字典列表
        params = []
        if hasattr(cls, "params"):
            for p in cls.params:
                if isinstance(p, dict):
                    # 字典格式
                    params.append({
                        "name": p.get("name"),
                        "type": p.get("type", "str"),
                        "default": p.get("default"),
                        "desc": p.get("desc", "")
                    })
                else:
                    # 字符串格式
                    params.append({
                        "name": str(p),
                        "type": "str",
                        "default": None,
                        "desc": ""
                    })

        strategies.append({
            "value": getattr(cls, "value", name),
            "text": name,
            "disable": False,
            "title": getattr(cls, "title", name),
            "description": getattr(cls, "description", ""),
            "level": getattr(cls, "level", "normal"),
            "params": params,
            "category": getattr(cls, "category", "General"),
        })

    #获取关注List
    #openid = request.query_params.get('openid')
    openid = "111"
    guanzhuList = []
    watchlist = Watchlist.objects.filter(openid=openid).first()
    if not watchlist:
        guanzhuList = []
    stocks = WatchlistStock.objects.filter(watchlist=watchlist)
    if not stocks.exists():
        guanzhuList = []
    else:
        for stock in stocks:
            guanzhuList.append(stock.stock_code)

    return Response({
        "code": 0,
        "message": "success",
        "count": len(strategies),
        "data": strategies,
        "guanzhuList": guanzhuList
    })

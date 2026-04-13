# bkapp/urls.py
from django.urls import path

from rest_framework_simplejwt import views as jwt_views

from .views.strategiesView import list_strategies
from .views.strategies2View import list_strategies2
from .views.userView import get_user_first_stock, get_user_subscriptions
from .views.skView import get_sk_k
from .views.skView import get_huice
from .views.skView import addToWatchlist
from .views.skView import removeFromWatchlist
from .views.momentumView import (
    momentum_backtest, momentum_optimize, etf_name_lookup, momentum_subscription,
)
from .views.meanrevView import meanrev_backtest, meanrev_optimize, meanrev_subscription
from .views.comboView import combo_backtest
from .views.authView import (
    register, login, me, captcha, send_email_code, reset_password,
)

urlpatterns = [
    #sk
    path('sk/strategies/', list_strategies),
    path('sk/getskk/', get_sk_k),
    path('sk/gethuice/', get_huice),
    path('sk/add/', addToWatchlist),
    path('sk/remove/', removeFromWatchlist),


    #find
    path('find/strategies2/', list_strategies2),
    path('find/stock/', list_strategies2),

    #momentum
    path('momentum/backtest/', momentum_backtest),
    path('momentum/optimize/', momentum_optimize),
    path('momentum/etf-names/', etf_name_lookup),
    path('momentum/subscription/', momentum_subscription),

    #meanrev
    path('meanrev/backtest/', meanrev_backtest),
    path('meanrev/optimize/', meanrev_optimize),
    path('meanrev/subscription/', meanrev_subscription),

    #combo
    path('combo/backtest/', combo_backtest),

    #mypage
    path('my/firststock/', get_user_first_stock),
    path('my/subscriptions/', get_user_subscriptions),

    #auth
    path('auth/captcha/', captcha),
    path('auth/send-code/', send_email_code),
    path('auth/register/', register),
    path('auth/login/', login),
    path('auth/reset-password/', reset_password),
    path('auth/me/', me),
    path('auth/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),

    # 保留 simplejwt 原生 endpoint（向后兼容）
    path('token/', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', jwt_views.TokenRefreshView.as_view()),
    path('token/verify/', jwt_views.TokenVerifyView.as_view()),
]

"""配额检查工具。

业务码约定：
  4001  非 VIP 回测/参数优化次数已用完
  4002  非 VIP 功能受限（订阅等仅 VIP 可用）
"""
from django.db.models import F


# VIP 权益文案（前后端共用）
VIP_INFO = (
    "VIP 权益：\n"
    "- 无限次回测\n"
    "- 无限次参数优化\n"
    "- 每日飞书信号订阅\n"
    "\n如需开通，请联系管理员微信：18623076530"
)


class QuotaExceeded(Exception):
    """非 VIP 配额已用完。"""
    pass


class VipRequired(Exception):
    """功能仅限 VIP 使用。"""
    pass


def check_and_inc_backtest(user):
    """非 VIP 用户每次回测/优化前调用。

    - VIP 直接放行，不计数
    - 非 VIP 检查 backtest_count < backtest_quota
      - 通过则原子 +1
      - 否则抛 QuotaExceeded
    """
    if not user or not user.is_authenticated:
        raise VipRequired("未登录")

    if user.is_vip:
        return  # VIP 不计数

    if user.backtest_count >= user.backtest_quota:
        raise QuotaExceeded(
            f"免费回测次数已用完（{user.backtest_count}/{user.backtest_quota}）"
        )

    # 原子自增，避免并发覆盖
    type(user).objects.filter(pk=user.pk).update(
        backtest_count=F('backtest_count') + 1
    )
    user.refresh_from_db(fields=['backtest_count'])


def require_vip(user):
    """订阅等仅 VIP 可用功能的入口检查。"""
    if not user or not user.is_authenticated:
        raise VipRequired("未登录")
    if not user.is_vip:
        raise VipRequired("此功能仅限 VIP 使用")

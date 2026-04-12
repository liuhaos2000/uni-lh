"""每日动量信号推送任务。

工作日早上 9:00 触发：
1. 遍历所有启用的 MomentumWatch 订阅
2. 对每个订阅重跑回测，取最后一天的信号
3. 通过飞书机器人推送给用户
"""
import logging
from datetime import datetime, date

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from ..models.momentum_watch import MomentumWatch
from ..logic.momentum.rotation_backtest import run_rotation_backtest
from ..logic.momentum.feishu import send_feishu_card, build_signal_card
from ..logic.momentum.email_push import send_signal_email
from ..views.momentumView import fetch_etf_history, fetch_etf_names

logger = logging.getLogger(__name__)


def _is_trade_day(d: date) -> bool:
    """判断给定日期是不是 A 股交易日（排除周末和法定节假日）。"""
    if d.weekday() >= 5:  # 周六/周日
        return False
    try:
        import chinese_calendar
        return chinese_calendar.is_workday(d) and not chinese_calendar.is_holiday(d)
    except ImportError:
        # 没装日历库就只过滤周末
        return True
    except (NotImplementedError, KeyError):
        # 库的日历未覆盖该年，保守按周末判断
        return True


@shared_task
def run_momentum_signals():
    """遍历所有启用的订阅，逐个推送信号。"""
    today = timezone.localtime().date()

    if not _is_trade_day(today):
        logger.info(f'{today} 非交易日，跳过动量信号推送')
        return f'{today} 非交易日'

    watches = MomentumWatch.objects.filter(enabled=True).select_related('user')
    total = watches.count()
    if total == 0:
        return 'no enabled watch'

    success = 0
    failed = 0
    for watch in watches:
        try:
            push_one_signal(watch)
            success += 1
        except Exception as e:
            logger.exception(f'推送 watch={watch.id} 失败: {e}')
            failed += 1

    msg = f'动量信号推送完成: total={total} success={success} failed={failed}'
    logger.info(msg)
    return msg


def push_one_signal(watch: MomentumWatch):
    """对单个订阅执行回测并推送飞书消息。"""
    etf_codes = list(watch.etf_codes or [])
    if len(etf_codes) < 2:
        logger.warning(f'watch={watch.id} 标的不足 2 个，跳过')
        return

    # 拉取每只 ETF 的历史数据（命中缓存即不重复请求）
    etf_history_dict = {}
    for code in etf_codes:
        try:
            data = fetch_etf_history(code, include_realtime=True)
            if not data:
                logger.warning(f'ETF {code} 无数据，跳过 watch={watch.id}')
                return
            etf_history_dict[code] = data
        except Exception as e:
            logger.error(f'获取 ETF {code} 历史数据失败: {e}')
            return

    etf_names = fetch_etf_names(etf_codes)

    # 起始日期：用 lookback_n × 3 倍历史数据保证足够回看
    # 简单起见，固定从 2024/01/01 开始（与前端默认一致）
    start_date = '2024/01/01'
    end_date = timezone.localtime().strftime('%Y/%m/%d')

    result = run_rotation_backtest(
        etf_history_dict=etf_history_dict,
        start_date=start_date,
        end_date=end_date,
        initial_capital=watch.initial_capital,
        lookback_n=watch.lookback_n,
        rebalance_days=watch.rebalance_days,
    )

    latest_signal = result.get('latest_signal')
    latest_date = result.get('latest_date')
    latest_scores = result.get('latest_scores') or {}

    if not latest_signal or not latest_date:
        logger.warning(f'watch={watch.id} 无信号数据')
        return

    # 校验最新交易日：必须是今天的前一个交易日，否则数据陈旧（节假日跳过等情况）
    today_str = timezone.localtime().strftime('%Y/%m/%d')
    if latest_date >= today_str:
        # 极端情况：已经包含今天的数据（盘中？）—— 仍然推送
        pass

    user = watch.user
    username = getattr(user, 'nickname', None) or user.username
    current_holding = result.get('current_holding')
    summary = result.get('summary', {})

    channel = (getattr(settings, 'PUSH_CHANNEL', 'email') or 'email').lower()
    action = latest_signal.get('action')

    email_ok = feishu_ok = None

    if channel in ('email', 'both'):
        if user.email:
            email_ok = send_signal_email(
                user.email,
                username=username,
                signal_date=latest_date,
                signal=latest_signal,
                scores=latest_scores,
                etf_names=etf_names,
                current_holding=current_holding,
                summary=summary,
            )
        else:
            logger.warning(f'watch={watch.id} ({username}) 用户未设置邮箱，跳过邮件')
            email_ok = False

    if channel in ('feishu', 'both'):
        card = build_signal_card(
            username=username,
            signal_date=latest_date,
            signal=latest_signal,
            scores=latest_scores,
            etf_names=etf_names,
            current_holding=current_holding,
            summary=summary,
        )
        feishu_ok = send_feishu_card(card)

    logger.info(
        f'watch={watch.id} ({username}) action={action} channel={channel} '
        f'email={email_ok} feishu={feishu_ok}'
    )

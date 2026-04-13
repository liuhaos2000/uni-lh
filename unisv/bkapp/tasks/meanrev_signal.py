"""每日均值回归信号推送任务。

工作日早上 9:00 触发：
1. 遍历所有启用的 MeanrevWatch 订阅
2. 对每个订阅重跑回测，取最后一天的信号
3. 通过飞书/邮件推送给用户
"""
import logging
from datetime import date

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from ..models.meanrev_watch import MeanrevWatch
from ..logic.meanrev.meanrev_backtest import run_meanrev_backtest
from ..logic.meanrev.signal import compute_signal
from ..logic.momentum.feishu import send_feishu_card
from ..logic.common.data_fetcher import fetch_etf_history, fetch_etf_names

logger = logging.getLogger(__name__)


def _is_trade_day(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    try:
        import chinese_calendar
        return chinese_calendar.is_workday(d) and not chinese_calendar.is_holiday(d)
    except ImportError:
        return True
    except (NotImplementedError, KeyError):
        return True


@shared_task
def run_meanrev_signals():
    """遍历所有启用的均值回归订阅，逐个推送信号。"""
    today = timezone.localtime().date()

    if not _is_trade_day(today):
        logger.info(f'{today} 非交易日，跳过均值回归信号推送')
        return f'{today} 非交易日'

    watches = MeanrevWatch.objects.filter(enabled=True).select_related('user')
    total = watches.count()
    if total == 0:
        return 'no enabled meanrev watch'

    success = 0
    failed = 0
    for watch in watches:
        try:
            push_one_meanrev_signal(watch)
            success += 1
        except Exception as e:
            logger.exception(f'推送 meanrev watch={watch.id} 失败: {e}')
            failed += 1

    msg = f'均值回归信号推送完成: total={total} success={success} failed={failed}'
    logger.info(msg)
    return msg


def push_one_meanrev_signal(watch: MeanrevWatch):
    """对单个订阅执行回测并推送消息。"""
    etf_codes = list(watch.etf_codes or [])
    if len(etf_codes) < 2:
        logger.warning(f'meanrev watch={watch.id} 标的不足 2 个，跳过')
        return

    etf_history_dict = {}
    for code in etf_codes:
        try:
            data = fetch_etf_history(code, include_realtime=True)
            if not data:
                logger.warning(f'ETF {code} 无数据，跳过 meanrev watch={watch.id}')
                return
            etf_history_dict[code] = data
        except Exception as e:
            logger.error(f'获取 ETF {code} 历史数据失败: {e}')
            return

    etf_names = fetch_etf_names(etf_codes)

    start_date = '2024/01/01'
    end_date = timezone.localtime().strftime('%Y/%m/%d')

    result = run_meanrev_backtest(
        etf_history_dict=etf_history_dict,
        start_date=start_date,
        end_date=end_date,
        initial_capital=watch.initial_capital,
        signal_type=watch.signal_type,
        period=watch.period,
        num_std=watch.num_std,
        stop_loss=watch.stop_loss,
        rebalance_days=watch.rebalance_days,
        oversold=watch.oversold,
        overbought=watch.overbought,
    )

    current_holding = result.get('current_holding')
    summary = result.get('summary', {})
    trade_records = result.get('trade_records', [])

    # 从偏离度曲线中取最新日期的各标的偏离度
    deviation_curves = result.get('deviation_curves', {})
    latest_deviations = {}
    for code, curve in deviation_curves.items():
        if curve:
            last = curve[-1]
            latest_deviations[code] = last[1]  # (date, deviation)

    # 取最新交易日
    equity_curve = result.get('equity_curve', [])
    if not equity_curve:
        logger.warning(f'meanrev watch={watch.id} 无回测数据')
        return
    latest_date = equity_curve[-1][0]

    # 构建信号描述
    if current_holding:
        action = 'hold'
        action_desc = f"持有 {etf_names.get(current_holding['etfCode'], current_holding['etfCode'])}"
    else:
        action = 'wait'
        action_desc = '空仓等待信号'

    # 检查最近一次交易是否在最新日期
    if trade_records:
        last_trade = trade_records[-1]
        if last_trade.get('sellDate') == latest_date:
            action = 'sell'
            action_desc = f"卖出 {etf_names.get(last_trade['etfCode'], last_trade['etfCode'])}（{last_trade.get('reason', '')}）"

    user = watch.user
    username = getattr(user, 'nickname', None) or user.username

    channel = (getattr(settings, 'PUSH_CHANNEL', 'email') or 'email').lower()

    email_ok = feishu_ok = None

    if channel in ('email', 'both'):
        if user.email:
            email_ok = _send_meanrev_email(
                user.email,
                username=username,
                signal_date=latest_date,
                action=action,
                action_desc=action_desc,
                deviations=latest_deviations,
                etf_names=etf_names,
                current_holding=current_holding,
                summary=summary,
                watch=watch,
            )
        else:
            logger.warning(f'meanrev watch={watch.id} ({username}) 用户未设置邮箱')
            email_ok = False

    if channel in ('feishu', 'both'):
        card = _build_meanrev_card(
            username=username,
            signal_date=latest_date,
            action=action,
            action_desc=action_desc,
            deviations=latest_deviations,
            etf_names=etf_names,
            current_holding=current_holding,
            summary=summary,
            watch=watch,
        )
        feishu_ok = send_feishu_card(card)

    logger.info(
        f'meanrev watch={watch.id} ({username}) action={action} channel={channel} '
        f'email={email_ok} feishu={feishu_ok}'
    )


_ACTION_EMOJI = {
    'hold': '⏸️',
    'sell': '🔴',
    'buy': '🟢',
    'wait': '⏳',
}
_ACTION_TEXT = {
    'hold': '持有',
    'sell': '卖出',
    'buy': '买入',
    'wait': '空仓等待',
}
_ACTION_COLOR = {
    'hold': 'grey',
    'sell': 'red',
    'buy': 'green',
    'wait': 'blue',
}


def _build_meanrev_card(*, username, signal_date, action, action_desc,
                        deviations, etf_names, current_holding, summary, watch):
    """构建均值回归信号飞书卡片。"""
    # 偏离度排序
    sorted_devs = sorted(
        deviations.items(),
        key=lambda x: x[1] if x[1] is not None else float('inf'),
    )
    dev_lines = []
    for code, dev in sorted_devs:
        name = etf_names.get(code, code)
        if dev is not None:
            dev_lines.append(f"`{code}` {name}　**{dev:+.4f}**")
        else:
            dev_lines.append(f"`{code}` {name}　数据不足")

    # 持仓块
    if current_holding:
        profit = current_holding.get('unrealizedProfit', 0) * 100
        profit_str = f"{'+' if profit >= 0 else ''}{profit:.2f}%"
        h_code = current_holding['etfCode']
        holding_label = f"{etf_names.get(h_code, h_code)} ({h_code})"
        holding_block = (
            f"标的：{holding_label}\n"
            f"买入：{current_holding['buyDate']} @ {current_holding['buyPrice']}\n"
            f"现价：{current_holding['currentPrice']}（{profit_str}）\n"
            f"持有：{current_holding['holdingDays']} 天"
        )
    else:
        holding_block = "空仓中"

    # 收益块
    final_eq = summary.get('final_equity', 0) or 0
    total_ret = (summary.get('total_return', 0) or 0) * 100
    summary_block = (
        f"权益：{final_eq / 10000:.2f} 万（{'+' if total_ret >= 0 else ''}{total_ret:.2f}%）\n"
        f"夏普：{summary.get('sharpe_ratio', 0)}　交易次数：{summary.get('total_trades', 0)}"
    )

    # 参数块
    signal_label = '布林带' if watch.signal_type == 'bollinger' else 'RSI'
    etf_labels = ' / '.join(
        f"{etf_names.get(c, c)}({c})" for c in (watch.etf_codes or [])
    ) or '—'
    params_block = (
        f"信号类型：**{signal_label}**　"
        f"周期：**{watch.period}** 天　"
        f"调仓：**{watch.rebalance_days}** 天\n"
    )
    if watch.signal_type == 'bollinger':
        params_block += f"标准差倍数：**{watch.num_std}**　"
    else:
        params_block += f"超卖阈值：**{watch.oversold}**　超买阈值：**{watch.overbought}**　"
    params_block += (
        f"止损：**{watch.stop_loss * 100:.0f}%**\n"
        f"初始资金：**{watch.initial_capital / 10000:.1f} 万**\n"
        f"标的池：{etf_labels}"
    )

    brand = getattr(settings, 'BRAND_NAME', '金点策略')
    title = f"{_ACTION_EMOJI.get(action, '📈')} {brand} · 均值回归 · {_ACTION_TEXT.get(action, '')}"

    card = {
        'config': {'wide_screen_mode': True},
        'header': {
            'title': {'tag': 'plain_text', 'content': title},
            'template': _ACTION_COLOR.get(action, 'blue'),
        },
        'elements': [
            {
                'tag': 'div',
                'text': {
                    'tag': 'lark_md',
                    'content': f"**用户：** {username}　　**信号日：** {signal_date}",
                },
            },
            {'tag': 'hr'},
            {
                'tag': 'div',
                'text': {
                    'tag': 'lark_md',
                    'content': f"**【今日状态】**\n{action_desc}",
                },
            },
            {'tag': 'hr'},
            {
                'tag': 'div',
                'text': {'tag': 'lark_md', 'content': f"**【模拟持仓】**\n{holding_block}"},
            },
            {'tag': 'hr'},
            {
                'tag': 'div',
                'text': {'tag': 'lark_md', 'content': f"**【模拟收益】**\n{summary_block}"},
            },
            {'tag': 'hr'},
            {
                'tag': 'div',
                'text': {
                    'tag': 'lark_md',
                    'content': "**【今日偏离度】**\n" + '\n'.join(dev_lines),
                },
            },
            {'tag': 'hr'},
            {
                'tag': 'div',
                'text': {'tag': 'lark_md', 'content': f"**【回测参数】**\n{params_block}"},
            },
            {
                'tag': 'note',
                'elements': [{'tag': 'plain_text', 'content': '仅供参考，不构成投资建议'}],
            },
        ],
    }
    return card


def _send_meanrev_email(to_email, *, username, signal_date, action, action_desc,
                        deviations, etf_names, current_holding, summary, watch):
    """发送均值回归信号邮件。"""
    from django.core.mail import EmailMultiAlternatives

    if not to_email:
        return False

    from_addr = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
    if not from_addr:
        logger.error('DEFAULT_FROM_EMAIL/EMAIL_HOST_USER 未配置')
        return False

    brand = getattr(settings, 'BRAND_NAME', '金点策略')
    signal_label = '布林带' if watch.signal_type == 'bollinger' else 'RSI'
    subject = f'【{brand}】{signal_date} 均值回归({signal_label}) · {_ACTION_TEXT.get(action, "信号")}'

    # 偏离度
    sorted_devs = sorted(
        deviations.items(),
        key=lambda x: x[1] if x[1] is not None else float('inf'),
    )
    dev_rows = []
    for code, dev in sorted_devs:
        name = etf_names.get(code, code)
        if dev is not None:
            dev_rows.append(f'{code} {name}  {dev:+.4f}')
        else:
            dev_rows.append(f'{code} {name}  数据不足')

    # 持仓
    if current_holding:
        profit = current_holding.get('unrealizedProfit', 0) * 100
        profit_str = f"{'+' if profit >= 0 else ''}{profit:.2f}%"
        h_code = current_holding['etfCode']
        holding_text = (
            f"标的：{etf_names.get(h_code, h_code)} ({h_code})\n"
            f"买入：{current_holding['buyDate']} @ {current_holding['buyPrice']}\n"
            f"现价：{current_holding['currentPrice']}（{profit_str}）\n"
            f"持有：{current_holding['holdingDays']} 天"
        )
    else:
        holding_text = '空仓中'

    final_eq = summary.get('final_equity', 0) or 0
    total_ret = (summary.get('total_return', 0) or 0) * 100

    text_body = '\n'.join([
        f'{brand} · 均值回归({signal_label})信号',
        f'用户：{username}　信号日：{signal_date}',
        '',
        f'【今日状态】{action_desc}',
        '',
        '【模拟持仓】',
        holding_text,
        '',
        f'【模拟收益】权益：{final_eq / 10000:.2f} 万（{total_ret:+.2f}%）',
        '',
        '【偏离度】',
        *dev_rows,
        '',
        '仅供参考，不构成投资建议',
    ])

    try:
        msg = EmailMultiAlternatives(subject, text_body, from_addr, [to_email])
        msg.send(fail_silently=False)
        return True
    except Exception as exc:
        logger.exception('均值回归邮件发送失败 %s: %s', to_email, exc)
        return False

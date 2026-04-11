"""飞书机器人推送模块（动量轮动信号）。"""
import os
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_feishu_card(card, webhook_url=None):
    """发送飞书机器人卡片消息。

    Args:
        card: 飞书 interactive 卡片字典
        webhook_url: 可选，覆盖默认 webhook
    """
    url = webhook_url or os.environ.get('FEISHU_WEBHOOK_URL')
    if not url:
        logger.warning('FEISHU_WEBHOOK_URL 未设置，跳过发送')
        return False

    payload = {'msg_type': 'interactive', 'card': card}
    try:
        r = requests.post(url, json=payload, timeout=10)
        data = r.json()
        if data.get('code', 0) != 0 and data.get('StatusCode', 0) != 0:
            logger.error(f'飞书发送失败: {data}')
            return False
        return True
    except Exception as e:
        logger.error(f'飞书发送异常: {e}')
        return False


_ACTION_EMOJI = {
    'hold': '⏸️',
    'sell': '🔴',
    'buy': '🟢',
    'swap': '🔄',
}
_ACTION_TEXT = {
    'hold': '持有不动',
    'sell': '清仓',
    'buy': '建仓买入',
    'swap': '调仓换股',
}
_ACTION_COLOR = {
    'hold': 'grey',
    'sell': 'red',
    'buy': 'green',
    'swap': 'orange',
}


def build_signal_card(username, signal_date, signal, scores, etf_names,
                      current_holding, summary):
    """构建动量信号飞书卡片。

    Args:
        username: 用户名（消息抬头展示）
        signal_date: 信号基于的交易日字符串 'YYYY/MM/DD' 或 'YYYY-MM-DD'
        signal: decide_signal 返回的字典
        scores: {code: score or None}
        etf_names: {code: name}
        current_holding: 模拟持仓 dict 或 None（信号执行后的状态）
        summary: 回测 summary
    """
    action = signal.get('action', 'hold')
    target = signal.get('target_code')
    target_name = etf_names.get(target, target) if target else None

    # ---- 操作描述 ----
    holding_label = ''
    if current_holding:
        h_code = current_holding['etfCode']
        holding_label = f"{etf_names.get(h_code, h_code)} ({h_code})"

    if action == 'swap':
        action_desc = f"卖出 {holding_label}\n买入 {target_name} ({target})"
    elif action == 'buy':
        action_desc = f"买入 {target_name} ({target})"
    elif action == 'sell':
        action_desc = f"清仓 {holding_label}"
    else:  # hold
        if current_holding:
            action_desc = f"继续持有 {holding_label}"
        else:
            action_desc = "继续空仓"

    if signal.get('is_rebalance_day'):
        exec_hint = '\n建议今日开盘下单'
    else:
        exec_hint = ''

    # ---- 评分排序 ----
    sorted_scores = sorted(
        scores.items(),
        key=lambda x: -(x[1] if x[1] is not None else float('-inf')),
    )
    score_lines = []
    for code, s in sorted_scores:
        name = etf_names.get(code, code)
        if s is None:
            score_lines.append(f"`{code}` {name}　数据不足")
        else:
            mark = ' ⭐' if code == target else ''
            score_lines.append(f"`{code}` {name}　**{s:+.4f}**{mark}")

    # ---- 持仓块 ----
    if current_holding:
        profit = current_holding.get('unrealizedProfit', 0) * 100
        profit_str = f"{'+' if profit >= 0 else ''}{profit:.2f}%"
        holding_block = (
            f"标的：{holding_label}\n"
            f"买入：{current_holding['buyDate']} @ {current_holding['buyPrice']}\n"
            f"现价：{current_holding['currentPrice']}（{profit_str}）\n"
            f"持有：{current_holding['holdingDays']} 天"
        )
    else:
        holding_block = "空仓中"

    # ---- 收益块 ----
    final_eq = summary.get('final_equity', 0) or 0
    total_ret = (summary.get('total_return', 0) or 0) * 100
    summary_block = (
        f"权益：{final_eq / 10000:.2f} 万（{'+' if total_ret >= 0 else ''}{total_ret:.2f}%）\n"
        f"夏普：{summary.get('sharpe_ratio', 0)}　交易次数：{summary.get('total_trades', 0)}"
    )

    # ---- 参数块 ----
    init_cap = summary.get('initial_capital', 0) or 0
    etf_code_list = summary.get('etf_codes', []) or []
    etf_labels = ' / '.join(
        f"{etf_names.get(c, c)}({c})" for c in etf_code_list
    ) or '—'
    params_block = (
        f"回看天数：**{summary.get('lookback_n', '-')}** 天　"
        f"调仓周期：**{summary.get('rebalance_days', '-')}** 天\n"
        f"初始资金：**{init_cap / 10000:.1f} 万**\n"
        f"回测区间：{summary.get('start_date', '-')} ~ {summary.get('end_date', '-')}\n"
        f"标的池：{etf_labels}"
    )

    brand = getattr(settings, 'BRAND_NAME', '金点策略')
    title = f"{_ACTION_EMOJI.get(action, '📈')} {brand} · 动量轮动 · {_ACTION_TEXT.get(action, '')}"

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
                    'content': f"**【今日操作】**\n{action_desc}{exec_hint}\n\n*原因：{signal.get('reason', '')}*",
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
                    'content': "**【今日动量评分】**\n" + '\n'.join(score_lines),
                },
            },
            {'tag': 'hr'},
            {
                'tag': 'div',
                'text': {'tag': 'lark_md', 'content': f"**【回测参数】**\n{params_block}"},
            },
            {
                'tag': 'note',
                'elements': [{
                    'tag': 'plain_text',
                    'content': '仅供参考，不构成投资建议',
                }],
            },
        ],
    }
    return card

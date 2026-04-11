"""动量信号邮件推送（HTML 邮件，按用户发送）。"""
import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


_ACTION_TEXT = {
    'hold': '继续持有',
    'sell': '清仓',
    'buy': '建仓买入',
    'swap': '调仓换股',
}
_ACTION_COLOR = {
    'hold': '#888888',
    'sell': '#D90214',
    'buy': '#16a34a',
    'swap': '#f59e0b',
}


def _build_summary_text(action, current_holding, target_code, target_name, etf_names):
    if action == 'swap':
        if current_holding:
            h_code = current_holding['etfCode']
            return f"{etf_names.get(h_code, h_code)} → {target_name}"
        return f"建仓 {target_name}"
    if action == 'buy':
        return f"建仓 {target_name}"
    if action == 'sell':
        if current_holding:
            h_code = current_holding['etfCode']
            return f"清仓 {etf_names.get(h_code, h_code)}"
        return "清仓"
    return _ACTION_TEXT.get(action, '维持原状')


def build_signal_email(*, username, signal_date, signal, scores, etf_names,
                       current_holding, summary):
    """生成 (subject, text_body, html_body)。"""
    action = signal.get('action', 'hold')
    target = signal.get('target_code')
    target_name = etf_names.get(target, target) if target else None
    color = _ACTION_COLOR.get(action, '#5470c6')

    brand = getattr(settings, 'BRAND_NAME', '金点策略')
    short_action = _build_summary_text(action, current_holding, target, target_name, etf_names)
    subject = f'【{brand}】{signal_date} 动量轮动 · {_ACTION_TEXT.get(action, "信号")}：{short_action}'

    # ---- 操作描述 ----
    if action == 'swap' and current_holding:
        h_code = current_holding['etfCode']
        action_desc = (
            f"卖出 {etf_names.get(h_code, h_code)} ({h_code})<br>"
            f"买入 {target_name} ({target})"
        )
    elif action == 'buy':
        action_desc = f"买入 {target_name} ({target})"
    elif action == 'sell' and current_holding:
        h_code = current_holding['etfCode']
        action_desc = f"清仓 {etf_names.get(h_code, h_code)} ({h_code})"
    elif action == 'hold' and current_holding:
        h_code = current_holding['etfCode']
        action_desc = f"继续持有 {etf_names.get(h_code, h_code)} ({h_code})"
    else:
        action_desc = '继续空仓'

    if signal.get('is_rebalance_day'):
        action_desc += '<br><em>建议今日开盘下单</em>'

    # ---- 评分 ----
    sorted_scores = sorted(
        scores.items(),
        key=lambda x: -(x[1] if x[1] is not None else float('-inf')),
    )
    score_rows = []
    for code, s in sorted_scores:
        name = etf_names.get(code, code)
        if s is None:
            score_rows.append(
                f'<tr><td style="padding:4px 8px;color:#999;">{code} {name}</td>'
                f'<td style="padding:4px 8px;color:#999;">数据不足</td></tr>'
            )
        else:
            star = ' ⭐' if code == target else ''
            score_rows.append(
                f'<tr><td style="padding:4px 8px;">{code} {name}</td>'
                f'<td style="padding:4px 8px;font-weight:bold;">{s:+.4f}{star}</td></tr>'
            )

    # ---- 持仓块 ----
    if current_holding:
        profit = current_holding.get('unrealizedProfit', 0) * 100
        profit_str = f"{'+' if profit >= 0 else ''}{profit:.2f}%"
        h_code = current_holding['etfCode']
        holding_block = (
            f"标的：{etf_names.get(h_code, h_code)} ({h_code})<br>"
            f"买入：{current_holding['buyDate']} @ {current_holding['buyPrice']}<br>"
            f"现价：{current_holding['currentPrice']}（{profit_str}）<br>"
            f"持有：{current_holding['holdingDays']} 天"
        )
    else:
        holding_block = '空仓中'

    # ---- 收益 ----
    final_eq = summary.get('final_equity', 0) or 0
    total_ret = (summary.get('total_return', 0) or 0) * 100
    summary_block = (
        f"权益：{final_eq / 10000:.2f} 万（{'+' if total_ret >= 0 else ''}{total_ret:.2f}%）<br>"
        f"夏普：{summary.get('sharpe_ratio', 0)}　交易次数：{summary.get('total_trades', 0)}"
    )

    # ---- 参数 ----
    init_cap = summary.get('initial_capital', 0) or 0
    etf_code_list = summary.get('etf_codes', []) or []
    etf_labels = ' / '.join(
        f'{etf_names.get(c, c)}({c})' for c in etf_code_list
    ) or '—'
    params_block = (
        f"回看：<b>{summary.get('lookback_n', '-')}</b> 天　"
        f"调仓：<b>{summary.get('rebalance_days', '-')}</b> 天<br>"
        f"初始资金：<b>{init_cap / 10000:.1f}</b> 万<br>"
        f"区间：{summary.get('start_date', '-')} ~ {summary.get('end_date', '-')}<br>"
        f"标的池：{etf_labels}"
    )

    html = f"""
<div style="font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; max-width: 640px; margin: 0 auto; color: #222;">
  <div style="background:{color};color:#fff;padding:18px 22px;border-radius:8px 8px 0 0;">
    <div style="font-size:18px;font-weight:600;">📈 {brand} · 动量轮动信号 · {_ACTION_TEXT.get(action, '')}</div>
    <div style="font-size:13px;opacity:.85;margin-top:4px;">用户：{username}　信号日：{signal_date}</div>
  </div>

  <div style="background:#fff;border:1px solid #eee;border-top:none;border-radius:0 0 8px 8px;padding:20px 22px;">

    <h3 style="margin:0 0 6px;font-size:15px;color:#333;">【今日操作】</h3>
    <div style="font-size:15px;line-height:1.6;">{action_desc}</div>
    <div style="font-size:12px;color:#888;margin-top:6px;">原因：{signal.get('reason', '')}</div>

    <hr style="border:none;border-top:1px solid #f0f0f0;margin:18px 0;">

    <h3 style="margin:0 0 6px;font-size:15px;color:#333;">【模拟持仓】</h3>
    <div style="font-size:13px;line-height:1.6;">{holding_block}</div>

    <hr style="border:none;border-top:1px solid #f0f0f0;margin:18px 0;">

    <h3 style="margin:0 0 6px;font-size:15px;color:#333;">【模拟收益】</h3>
    <div style="font-size:13px;line-height:1.6;">{summary_block}</div>

    <hr style="border:none;border-top:1px solid #f0f0f0;margin:18px 0;">

    <h3 style="margin:0 0 6px;font-size:15px;color:#333;">【今日动量评分】</h3>
    <table style="border-collapse:collapse;font-size:13px;">{''.join(score_rows)}</table>

    <hr style="border:none;border-top:1px solid #f0f0f0;margin:18px 0;">

    <h3 style="margin:0 0 6px;font-size:15px;color:#333;">【回测参数】</h3>
    <div style="font-size:13px;line-height:1.6;color:#555;">{params_block}</div>

    <div style="margin-top:20px;padding-top:14px;border-top:1px solid #f0f0f0;font-size:11px;color:#999;text-align:center;">
      仅供参考，不构成投资建议
    </div>
  </div>
</div>
"""

    text_lines = [
        f'{brand} · 动量轮动信号 · {_ACTION_TEXT.get(action, "")}',
        f'用户：{username}　信号日：{signal_date}',
        '',
        '【今日操作】',
        action_desc.replace('<br>', '\n').replace('<em>', '').replace('</em>', ''),
        f'原因：{signal.get("reason", "")}',
        '',
        '【模拟持仓】',
        holding_block.replace('<br>', '\n'),
        '',
        '【模拟收益】',
        summary_block.replace('<br>', '\n'),
        '',
        '仅供参考，不构成投资建议',
    ]
    text_body = '\n'.join(text_lines)

    return subject, text_body, html


def send_signal_email(to_email, *, username, signal_date, signal, scores,
                      etf_names, current_holding, summary):
    """发送动量信号邮件。返回 True/False。"""
    if not to_email:
        logger.warning('收件邮箱为空，跳过')
        return False

    from_addr = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
    if not from_addr:
        logger.error('DEFAULT_FROM_EMAIL/EMAIL_HOST_USER 未配置')
        return False

    subject, text_body, html_body = build_signal_email(
        username=username,
        signal_date=signal_date,
        signal=signal,
        scores=scores,
        etf_names=etf_names,
        current_holding=current_holding,
        summary=summary,
    )

    try:
        msg = EmailMultiAlternatives(subject, text_body, from_addr, [to_email])
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)
        return True
    except Exception as exc:
        logger.exception('邮件发送失败 %s: %s', to_email, exc)
        return False

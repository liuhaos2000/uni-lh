/**
 * VIP 相关提示工具。
 *
 * 后端业务码：
 *   4001  非 VIP 回测/优化次数已用完
 *   4002  非 VIP 功能受限（订阅）
 */

const DEFAULT_VIP_INFO =
  'VIP 权益：\n' +
  '- 无限次回测\n' +
  '- 无限次参数优化\n' +
  '- 每日飞书信号订阅\n' +
  '\n如需开通，请联系管理员微信：18623076530'

/**
 * 弹 VIP 提示框
 * @param {string} title    弹窗标题
 * @param {string} message  正文（来自后端 vip_info，没有则用默认）
 */
export function showVipDialog(title, message) {
  uni.showModal({
    title: title || '需要 VIP',
    content: message || DEFAULT_VIP_INFO,
    showCancel: false,
    confirmText: '我知道了',
  })
}

/**
 * 检查响应里的业务码，如果是 VIP 相关的就弹窗并返回 true
 * @param {Object} res  request() 返回的 data
 * @returns {boolean}   true 表示已处理（拦截掉了），调用方应停止后续逻辑
 */
export function handleVipBlocked(res) {
  if (!res || typeof res.code !== 'number') return false
  if (res.code === 4001) {
    showVipDialog('回测次数已用完', res.vip_info || DEFAULT_VIP_INFO)
    return true
  }
  if (res.code === 4002) {
    showVipDialog('此功能仅限 VIP', res.vip_info || DEFAULT_VIP_INFO)
    return true
  }
  return false
}

export default { showVipDialog, handleVipBlocked }

import request from '@/utils/request.js'

const BASE = '/meanrev/subscriptions/'

/** 获取当前用户全部均值回归订阅 */
export const listSubscriptions = () =>
  request({ url: BASE, method: 'GET', silent: true })

/** 获取单条订阅 */
export const getSubscription = (id) =>
  request({ url: `${BASE}${id}/`, method: 'GET', silent: true })

/** 创建一条新订阅 */
export const createSubscription = (params) =>
  request({ url: BASE, method: 'POST', data: params })

/** 更新订阅参数（不改 name） */
export const updateSubscription = (id, params) =>
  request({ url: `${BASE}${id}/`, method: 'PUT', data: params })

/** 删除订阅 */
export const deleteSubscription = (id) =>
  request({ url: `${BASE}${id}/`, method: 'DELETE' })

/** 切换通知开关 */
export const setSubscriptionNotify = (id, enabled) =>
  request({ url: `${BASE}${id}/notify/`, method: 'PATCH', data: { enabled } })

export default {
  listSubscriptions,
  getSubscription,
  createSubscription,
  updateSubscription,
  deleteSubscription,
  setSubscriptionNotify,
}

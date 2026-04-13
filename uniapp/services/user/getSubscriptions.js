import request from '@/utils/request.js'

/**
 * 获取当前用户的所有策略订阅（需登录）
 */
export const getSubscriptions = () =>
  request({ url: '/my/subscriptions/', method: 'GET' })

export default getSubscriptions

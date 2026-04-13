import request from '@/utils/request.js'

const URL = '/meanrev/subscription/'

/**
 * 查询当前订阅状态（需登录）
 */
export const getSubscription = () =>
  request({ url: URL, method: 'GET', silent: true })

/**
 * 创建或更新订阅
 */
export const saveSubscription = (params) =>
  request({
    url: URL,
    method: 'POST',
    data: params,
  })

/**
 * 取消订阅
 */
export const deleteSubscription = () =>
  request({ url: URL, method: 'DELETE' })

export default { getSubscription, saveSubscription, deleteSubscription }

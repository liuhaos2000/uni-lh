import ENV from '@/config/env.js'

const API_URL = `${ENV.API.BASE_URL}/momentum/subscription/`

// TODO: 接入登录后从全局取真实 user_id
const DEFAULT_USER_ID = 1

/**
 * 查询当前订阅状态
 */
export const getSubscription = async (userId = DEFAULT_USER_ID) => {
  try {
    const res = await uni.request({
      url: `${API_URL}?user_id=${userId}`,
      method: 'GET',
      timeout: 10000,
    })
    return res.data
  } catch (e) {
    console.error('查询订阅失败：', e)
    throw e
  }
}

/**
 * 创建或更新订阅
 */
export const saveSubscription = async (params, userId = DEFAULT_USER_ID) => {
  try {
    const res = await uni.request({
      url: API_URL,
      method: 'POST',
      data: { ...params, user_id: userId },
      header: { 'Content-Type': 'application/json' },
      timeout: 10000,
    })
    return res.data
  } catch (e) {
    console.error('保存订阅失败：', e)
    throw e
  }
}

/**
 * 取消订阅
 */
export const deleteSubscription = async (userId = DEFAULT_USER_ID) => {
  try {
    const res = await uni.request({
      url: `${API_URL}?user_id=${userId}`,
      method: 'DELETE',
      timeout: 10000,
    })
    return res.data
  } catch (e) {
    console.error('取消订阅失败：', e)
    throw e
  }
}

export default { getSubscription, saveSubscription, deleteSubscription }

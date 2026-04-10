import ENV from '@/config/env.js'

const API_URL = `${ENV.API.BASE_URL}/momentum/optimize`

/**
 * 参数优化接口
 * @param {Object} params
 * @param {string} params.codes
 * @param {string} params.start_date
 * @param {string} params.end_date
 * @param {number} params.initial_capital
 * @param {string} params.n_list - 回看天数列表，逗号分隔
 * @param {string} params.r_list - 调仓周期列表，逗号分隔
 */
export const getMomentumOptimize = async (params = {}) => {
  const query = new URLSearchParams()
  if (params.codes) query.append('codes', params.codes)
  if (params.start_date) query.append('start_date', params.start_date)
  if (params.end_date) query.append('end_date', params.end_date)
  if (params.initial_capital) query.append('initial_capital', params.initial_capital)
  if (params.n_list) query.append('n_list', params.n_list)
  if (params.r_list) query.append('r_list', params.r_list)

  const url = `${API_URL}?${query.toString()}`

  try {
    const response = await uni.request({ url, method: 'GET', timeout: 60000 })
    return response.data
  } catch (error) {
    console.error('参数优化请求失败：', error)
    throw error
  }
}

export default getMomentumOptimize

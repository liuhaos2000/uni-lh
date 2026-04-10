import ENV from '@/config/env.js'

const API_URL = `${ENV.API.BASE_URL}/momentum/backtest`

/**
 * 调用动量轮动回测接口
 * @param {Object} params
 * @param {string} params.codes - ETF代码，逗号分隔
 * @param {string} params.start_date - 起始日期 YYYY/MM/DD
 * @param {number} params.lookback_n - 回看天数
 * @param {number} params.rebalance_days - 调仓周期
 * @param {number} params.initial_capital - 初始资金
 */
export const getMomentumBacktest = async (params = {}) => {
  const query = new URLSearchParams()
  if (params.codes) query.append('codes', params.codes)
  if (params.start_date) query.append('start_date', params.start_date)
  if (params.end_date) query.append('end_date', params.end_date)
  if (params.lookback_n) query.append('lookback_n', params.lookback_n)
  if (params.rebalance_days) query.append('rebalance_days', params.rebalance_days)
  if (params.initial_capital) query.append('initial_capital', params.initial_capital)

  const url = `${API_URL}?${query.toString()}`

  try {
    const response = await uni.request({ url, method: 'GET', timeout: 30000 })
    return response.data
  } catch (error) {
    console.error('动量回测请求失败：', error)
    throw error
  }
}

export default getMomentumBacktest

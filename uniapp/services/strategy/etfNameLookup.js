import ENV from '@/config/env.js'

const API_URL = `${ENV.API.BASE_URL}/momentum/etf-names`

/**
 * 查询ETF名称
 * @param {string} codes - 逗号分隔的ETF代码
 * @returns {Promise<Object>} {code: name}
 */
export const etfNameLookup = async (codes) => {
  const url = `${API_URL}?codes=${encodeURIComponent(codes)}`
  try {
    const response = await uni.request({ url, method: 'GET', timeout: 10000 })
    if (response.data && response.data.code === 0) {
      return response.data.data
    }
    return {}
  } catch (error) {
    console.error('ETF名称查询失败：', error)
    return {}
  }
}

export default etfNameLookup

// 导入全局配置
import ENV from '@/config/env.js'

const API_URL = `${ENV.API.BASE_URL}`

export const addToWatchlist = async (stock_code) => {
  // 若使用 mock，可在此返回模拟数据
  try {
    const response = await uni.request({ url: `${API_URL}/sk/add/`, method: 'POST', timeout: ENV.API.TIMEOUT, data: { stock_code } })
    return response.data
  } catch (error) {
    console.error('添加自选失败：', error)
    throw error
  }
}

export const removeFromWatchlist = async (stock_code) => {
  try {
    const response = await uni.request({ url: `${API_URL}/sk/remove/`, method: 'POST', timeout: ENV.API.TIMEOUT, data: { stock_code } })
    return response.data
  } catch (error) {
    console.error('取消自选失败：', error)
    throw error
  }
}

export default { addToWatchlist, removeFromWatchlist }

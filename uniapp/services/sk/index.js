// 导入全局配置与 mock 数据
import ENV from '@/config/env.js'
import mockData from '@/mock/sk/init/data.json'

const API_URL = `${ENV.API.BASE_URL}/sk/getskk`

export const getSkInitData = async (skId) => {
  if (ENV.USE_MOCK) {
    if (ENV.MOCK.DELAY > 0) await new Promise(r => setTimeout(r, ENV.MOCK.DELAY))
    return mockData
  }

  try {
    const response = await uni.request({ url: `${API_URL}?skId=${skId}`, method: 'GET', timeout: ENV.API.TIMEOUT })
    return response.data
  } catch (error) {
    console.error('获取 sk 初始数据失败：', error)
    throw error
  }
}

export default getSkInitData

// 导入全局配置与 mock 数据
import ENV from '@/config/env.js'
import mockData from '@/mock/sk/getMy/data.json'

const API_URL = `${ENV.API.BASE_URL}/my/firststock`

export const getMy = async () => {

  if (ENV.USE_MOCK) {
    if (ENV.MOCK.DELAY > 0) await new Promise(r => setTimeout(r, ENV.MOCK.DELAY))
    return mockData
  }

  try {
    const response = await uni.request({ url: API_URL, method: 'GET', timeout: ENV.API.TIMEOUT,data:{} })
    return response.data
  } catch (error) {
    console.error('获取 sk 初始数据失败：', error)
    throw error
  }
}

export default getMy

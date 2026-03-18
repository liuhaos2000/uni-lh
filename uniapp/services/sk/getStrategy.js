// 导入全局配置与 mock 数据
import ENV from '@/config/env.js'


const API_URL = `${ENV.API.BASE_URL}/sk/strategies`

export const getStrategies = async () => {

  // if (ENV.USE_MOCK) {
  //   if (ENV.MOCK.DELAY > 0) await new Promise(r => setTimeout(r, ENV.MOCK.DELAY))
  //   return mockData
  // }

  try {
    const response = await uni.request({ url: API_URL, method: 'GET', timeout: ENV.API.TIMEOUT})
    return response.data
  } catch (error) {
    console.error('获取 sk 策略下拉框数据失败：', error)
    throw error
  }
}

export default getStrategies

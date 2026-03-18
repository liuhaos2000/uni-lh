// 导入全局配置
import ENV from '@/config/env.js'

// 导入mock数据
import mockData from '@/mock/main/main01/init/data.json'

// 构建API URL
const API_URL = `${ENV.API.BASE_URL}/${ENV.API.VERSION}/main01/init`

/**
 * 获取表单初始化数据
 * @returns {Promise} 返回表单数据
 */
export const getFormInitData = async () => {
  if (ENV.USE_MOCK) {
    // 模拟网络延迟
    if (ENV.MOCK.DELAY > 0) {
      await new Promise(resolve => setTimeout(resolve, ENV.MOCK.DELAY))
    }
    // 返回mock数据
    return mockData
  }
  
  // 实际API请求
  try {
    const response = await uni.request({
      url: API_URL,
      method: 'GET',
      timeout: ENV.API.TIMEOUT
    })
    return response.data
  } catch (error) {
    console.error('获取表单初始数据失败：', error)
    throw error
  }
}
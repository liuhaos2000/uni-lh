import ENV from '@/config/env.js'
import mockData from '@/mock/sk/getHuice/data.json'
import request from '@/utils/request.js'

export const getHuiceData = async (skId, celueId) => {
  if (ENV.USE_MOCK) {
    if (ENV.MOCK.DELAY > 0) await new Promise((r) => setTimeout(r, ENV.MOCK.DELAY))
    return mockData
  }
  return request({
    url: '/sk/gethuice',
    method: 'GET',
    data: { skId, celueId },
  })
}

export default getHuiceData

import ENV from '@/config/env.js'
import mockData from '@/mock/sk/getMy/data.json'
import request from '@/utils/request.js'

export const getMy = async () => {
  if (ENV.USE_MOCK) {
    if (ENV.MOCK.DELAY > 0) await new Promise((r) => setTimeout(r, ENV.MOCK.DELAY))
    return mockData
  }
  return request({ url: '/my/firststock', method: 'GET', silent: true })
}

export default getMy

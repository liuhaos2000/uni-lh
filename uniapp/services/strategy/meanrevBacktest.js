import request from '@/utils/request.js'

/**
 * 调用均值回归回测接口（需登录）
 */
export const getMeanrevBacktest = (params = {}) =>
  request({
    url: '/meanrev/backtest',
    method: 'GET',
    data: params,
    timeout: 30000,
  })

export default getMeanrevBacktest

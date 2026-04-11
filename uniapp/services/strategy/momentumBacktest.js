import request from '@/utils/request.js'

/**
 * 调用动量轮动回测接口（需登录）
 */
export const getMomentumBacktest = (params = {}) =>
  request({
    url: '/momentum/backtest',
    method: 'GET',
    data: params,
    timeout: 30000,
  })

export default getMomentumBacktest

import request from '@/utils/request.js'

/**
 * 参数优化接口（需登录）
 */
export const getMomentumOptimize = (params = {}) =>
  request({
    url: '/momentum/optimize',
    method: 'GET',
    data: params,
    timeout: 60000,
  })

export default getMomentumOptimize

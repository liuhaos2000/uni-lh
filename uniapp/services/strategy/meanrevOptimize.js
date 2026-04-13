import request from '@/utils/request.js'

/**
 * 均值回归参数优化接口（需登录）
 */
export const getMeanrevOptimize = (params = {}) =>
  request({
    url: '/meanrev/optimize',
    method: 'GET',
    data: params,
    timeout: 60000,
  })

export default getMeanrevOptimize

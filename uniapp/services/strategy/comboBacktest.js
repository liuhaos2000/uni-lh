import request from '@/utils/request.js'

/**
 * 组合策略回测接口（POST，需登录）
 */
export const postComboBacktest = (data = {}) =>
  request({
    url: '/combo/backtest/',
    method: 'POST',
    data,
    timeout: 60000,
  })

export default postComboBacktest

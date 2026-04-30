import request from '@/utils/request.js'

/**
 * 多维条件策略回测（需登录）。维度：趋势 / 动量 / 量价 / 风控
 * params: { stock_code, start_date, end_date, initial_capital,
 *           trend_enabled, trend_short_period, trend_long_period,
 *           momentum_enabled, momentum_period,
 *           volprice_enabled, volprice_ratio_period, volprice_flow_period, volprice_ratio_threshold,
 *           risk_enabled, risk_lookback, risk_drawdown_threshold,
 *           min_match_count }
 *
 * min_match_count: 0 或缺省 = 启用维度全部满足（AND）；
 *                  整数 N >= 1 = 启用维度里满足数量 ≥ N 即开仓
 */
export const getMultidimBacktest = (params = {}) =>
	request({
		url: '/multidim/backtest',
		method: 'GET',
		data: params,
		timeout: 30000,
	})

export default getMultidimBacktest

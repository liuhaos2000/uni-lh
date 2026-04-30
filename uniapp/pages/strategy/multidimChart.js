/**
 * 多维条件策略图表（ECharts，v2 维度）。
 *
 * 布局：
 *   grid0  K线 + MA(short) + MA(long)
 *   grid1  成交量柱 + 量比基准（ratio_period 日均量）
 *   grid2  动量百分比折线 + 0% 基准线
 *   grid3  权益：策略 vs 买入持有基准
 *   grid4  条件格子：4 行 heatmap（趋势/动量/量价/风控）
 *
 * 五个 grid 共用一套 xAxis 数据（category），dataZoom 同时绑定五个 xAxisIndex。
 */
import { onBeforeUnmount, ref } from 'vue'

let chart = null
let _touchCleanup = null

// ── touch 捏合缩放 + 单指平移 ──
function attachTouchZoom(dom) {
	if (_touchCleanup) _touchCleanup()
	let startDist = 0
	let startZoom = { start: 50, end: 100 }
	let lastSingleX = null
	let startSingleX = null
	let isDragging = false

	function getZoomState() {
		if (!chart) return { start: 50, end: 100 }
		const opt = chart.getOption()
		const dz = opt.dataZoom && opt.dataZoom[0]
		return dz ? { start: dz.start, end: dz.end } : { start: 50, end: 100 }
	}
	function pinchDist(t) {
		const dx = t[0].clientX - t[1].clientX
		const dy = t[0].clientY - t[1].clientY
		return Math.sqrt(dx * dx + dy * dy)
	}
	function onTouchStart(e) {
		if (e.touches.length === 2) {
			startDist = pinchDist(e.touches)
			startZoom = getZoomState()
			e.preventDefault()
		} else if (e.touches.length === 1) {
			lastSingleX = e.touches[0].clientX
			startSingleX = e.touches[0].clientX
			isDragging = false
		}
	}
	function onTouchMove(e) {
		if (e.touches.length === 2) {
			e.preventDefault()
			const newDist = pinchDist(e.touches)
			if (!startDist) return
			const ratio = startDist / newDist
			const range = startZoom.end - startZoom.start
			const newRange = Math.min(100, Math.max(3, range * ratio))
			const mid = (startZoom.start + startZoom.end) / 2
			let ns = mid - newRange / 2
			let ne = mid + newRange / 2
			if (ns < 0) { ne -= ns; ns = 0 }
			if (ne > 100) { ns -= (ne - 100); ne = 100 }
			chart && chart.dispatchAction({ type: 'dataZoom', dataZoomIndex: 0, start: Math.max(0, ns), end: Math.min(100, ne) })
		} else if (e.touches.length === 1 && lastSingleX !== null) {
			const cur = e.touches[0].clientX
			const totalDx = Math.abs(cur - startSingleX)
			if (totalDx > 5) isDragging = true
			if (!isDragging) return
			e.preventDefault()
			const dx = cur - lastSingleX
			lastSingleX = cur
			const { start, end } = getZoomState()
			const range = end - start
			const shift = -(dx / dom.offsetWidth) * range
			let ns = start + shift
			let ne = end + shift
			if (ns < 0) { ne -= ns; ns = 0 }
			if (ne > 100) { ns -= (ne - 100); ne = 100 }
			chart && chart.dispatchAction({ type: 'dataZoom', dataZoomIndex: 0, start: Math.max(0, ns), end: Math.min(100, ne) })
		}
	}
	function onTouchEnd() {
		startDist = 0
		lastSingleX = null
		startSingleX = null
		isDragging = false
	}
	dom.addEventListener('touchstart', onTouchStart, { passive: false })
	dom.addEventListener('touchmove', onTouchMove, { passive: false })
	dom.addEventListener('touchend', onTouchEnd)
	_touchCleanup = () => {
		dom.removeEventListener('touchstart', onTouchStart)
		dom.removeEventListener('touchmove', onTouchMove)
		dom.removeEventListener('touchend', onTouchEnd)
		_touchCleanup = null
	}
}

async function loadEcharts() {
	try {
		const mod = await import(/* @vite-ignore */ 'echarts')
		return mod.default || mod
	} catch (err) {
		if (typeof window !== 'undefined' && window.echarts) return window.echarts
		await new Promise((resolve, reject) => {
			const s = document.createElement('script')
			s.src = 'https://fastly.jsdelivr.net/npm/echarts@5/dist/echarts.min.js'
			s.onload = () => resolve()
			s.onerror = (e) => reject(e)
			document.head.appendChild(s)
		})
		return window.echarts
	}
}

// chart_data.kline: [[date,o,h,l,c], ...] → ECharts candlestick 期望 [o,c,l,h]
function toCandle(values) {
	return values.map(r => [r[1], r[4], r[3], r[2]])
}

function buildOption(chartData, params, enabledFlags, title) {
	const categories = chartData.dates || []
	const candles = toCandle(chartData.kline || [])
	const maShort = chartData.trend_ma_short || []
	const maLong = chartData.trend_ma_long || []
	const volBars = (chartData.volumes || []).map(r => ({
		value: r[1],
		itemStyle: { color: r[2] > 0 ? '#ec0000' : '#00da3c' },
	}))
	const volMaRecent = chartData.vol_ma_recent || []
	const volMaBasis = chartData.vol_ma_basis || []
	const momentumPct = chartData.momentum_pct || []
	const equity = chartData.equity || []
	const benchmark = chartData.benchmark || []
	const flags = chartData.flags || {}

	// 条件格子：rowIdx: 0=趋势 1=动量 2=量价 3=风控
	const dimOrder = ['trend', 'momentum', 'volprice', 'risk']
	const heatData = []
	for (let col = 0; col < categories.length; col++) {
		for (let r = 0; r < dimOrder.length; r++) {
			const dim = dimOrder[r]
			const arr = flags[dim] || []
			const enabled = enabledFlags[dim]
			let v
			if (!enabled) v = -1
			else v = arr[col] ? 1 : 0
			heatData.push([col, r, v])
		}
	}

	const grid = [
		{ left: 56, right: 16, top: 40, height: '28%' },       // K线
		{ left: 56, right: 16, top: '38%', height: '11%' },    // 成交量
		{ left: 56, right: 16, top: '53%', height: '11%' },    // 动量
		{ left: 56, right: 16, top: '68%', height: '14%' },    // 权益
		{ left: 56, right: 16, top: '86%', height: '8%' },     // 格子
	]

	const xAxisBase = {
		type: 'category',
		data: categories,
		boundaryGap: true,
		axisLine: { onZero: false },
		splitLine: { show: false },
		axisLabel: { show: false },
		axisTick: { show: false },
	}
	const xAxis = [
		{ ...xAxisBase, gridIndex: 0 },
		{ ...xAxisBase, gridIndex: 1 },
		{ ...xAxisBase, gridIndex: 2 },
		{ ...xAxisBase, gridIndex: 3 },
		{
			...xAxisBase,
			gridIndex: 4,
			axisLabel: { show: true, fontSize: 9, color: '#888' },
		},
	]

	// 权益 y 轴范围
	const eqAll = []
	for (const v of equity) if (v != null) eqAll.push(v)
	for (const v of benchmark) if (v != null) eqAll.push(v)
	const eqMin = eqAll.length ? Math.min(...eqAll) : 0
	const eqMax = eqAll.length ? Math.max(...eqAll) : 1

	const yAxis = [
		{ scale: true, gridIndex: 0, splitArea: { show: true }, axisLabel: { fontSize: 10 } },
		{ scale: true, gridIndex: 1, splitLine: { show: false }, axisLabel: { fontSize: 10 } },
		{
			scale: true,
			gridIndex: 2,
			splitLine: { show: false },
			axisLabel: {
				fontSize: 10,
				formatter: (v) => (v * 100).toFixed(1) + '%',
			},
		},
		{
			gridIndex: 3,
			scale: true,
			min: eqMin,
			max: eqMax,
			splitLine: { show: false },
			axisLabel: {
				fontSize: 10,
				formatter: (v) => (v >= 1e8 ? (v / 1e8).toFixed(2) + '亿'
					: v >= 1e4 ? (v / 1e4).toFixed(1) + '万' : v.toFixed(0)),
			},
		},
		{
			gridIndex: 4,
			type: 'category',
			data: ['趋势', '动量', '量价', '风控'],
			boundaryGap: true,
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: { fontSize: 10 },
			splitLine: { show: false },
		},
	]

	const series = [
		// K线
		{
			name: 'K线',
			type: 'candlestick',
			xAxisIndex: 0,
			yAxisIndex: 0,
			data: candles,
			itemStyle: {
				color: '#ec0000',
				color0: '#00da3c',
				borderColor: '#8A0000',
				borderColor0: '#008F28',
			},
		},
		// 短均线
		{
			name: `MA${params.trend_short || 20}`,
			type: 'line',
			xAxisIndex: 0,
			yAxisIndex: 0,
			data: maShort,
			smooth: true,
			showSymbol: false,
			lineStyle: { width: 1.2, color: '#ffa200' },
		},
		// 长均线
		{
			name: `MA${params.trend_long || 60}`,
			type: 'line',
			xAxisIndex: 0,
			yAxisIndex: 0,
			data: maLong,
			smooth: true,
			showSymbol: false,
			lineStyle: { width: 1.2, color: '#1976d2' },
		},
		// 成交量柱
		{
			name: '成交量',
			type: 'bar',
			xAxisIndex: 1,
			yAxisIndex: 1,
			data: volBars,
		},
		// 近期均量（量比分子）
		{
			name: `近期量 MA${params.vol_flow_period || 5}`,
			type: 'line',
			xAxisIndex: 1,
			yAxisIndex: 1,
			data: volMaRecent,
			smooth: true,
			showSymbol: false,
			lineStyle: { width: 1.2, color: '#1976d2' },
		},
		// 量比基准（量比分母）
		{
			name: `基准量 MA${params.vol_ratio_period || 20}`,
			type: 'line',
			xAxisIndex: 1,
			yAxisIndex: 1,
			data: volMaBasis,
			smooth: true,
			showSymbol: false,
			lineStyle: { width: 1, color: '#8e24aa' },
		},
		// 动量折线
		{
			name: `动量${params.momentum_period || 60}日`,
			type: 'line',
			xAxisIndex: 2,
			yAxisIndex: 2,
			data: momentumPct,
			smooth: true,
			showSymbol: false,
			lineStyle: { width: 1.2, color: '#ef6c00' },
			markLine: {
				symbol: 'none',
				silent: true,
				lineStyle: { type: 'dashed', color: '#888', width: 1 },
				label: { formatter: '0%' },
				data: [{ yAxis: 0 }],
			},
		},
		// 策略权益
		{
			name: '策略权益',
			type: 'line',
			xAxisIndex: 3,
			yAxisIndex: 3,
			data: equity,
			smooth: true,
			showSymbol: false,
			lineStyle: { width: 1.4, color: '#ec0000' },
		},
		// 基准
		{
			name: '基准(买入持有)',
			type: 'line',
			xAxisIndex: 3,
			yAxisIndex: 3,
			data: benchmark,
			smooth: true,
			showSymbol: false,
			lineStyle: { width: 1.2, color: '#888', type: 'dashed' },
		},
		// 条件格子
		{
			name: '条件',
			type: 'heatmap',
			xAxisIndex: 4,
			yAxisIndex: 4,
			data: heatData,
			label: { show: false },
			itemStyle: { borderColor: '#fff', borderWidth: 1 },
		},
	]

	// visualMap 给 heatmap 上色（series[9]）
	const visualMap = {
		show: false,
		type: 'piecewise',
		seriesIndex: 9,
		pieces: [
			{ value: -1, color: '#e0e0e0' },
			{ value: 0, color: '#f0f0f0' },
			{ value: 1, color: '#ec0000' },
		],
	}

	const dataZoom = [
		{ type: 'inside', xAxisIndex: [0, 1, 2, 3, 4], start: 50, end: 100 },
		{ show: true, type: 'slider', xAxisIndex: [0, 1, 2, 3, 4], bottom: 4, height: 16, start: 50, end: 100 },
	]

	return {
		title: { text: title || '', left: 0, textStyle: { fontSize: 13 } },
		tooltip: {
			trigger: 'axis',
			axisPointer: { type: 'cross', link: [{ xAxisIndex: 'all' }] },
		},
		axisPointer: { link: [{ xAxisIndex: 'all' }] },
		grid,
		xAxis,
		yAxis,
		dataZoom,
		visualMap,
		series,
	}
}

export function useMultidimChart() {
	const loading = ref(false)

	async function render(containerId, { chartData, dimensionParams, enabledFlags, title }) {
		loading.value = true
		try {
			const echarts = await loadEcharts()
			const dom = document.getElementById(containerId)
			if (!dom) throw new Error('chart container not found: ' + containerId)
			if (!chart) {
				chart = echarts.init(dom)
				attachTouchZoom(dom)
			}
			const option = buildOption(chartData, dimensionParams || {}, enabledFlags || {}, title)
			chart.setOption(option, true)
		} catch (e) {
			console.error('multidim chart render error:', e)
			throw e
		} finally {
			loading.value = false
		}
	}

	function resize() {
		if (chart && typeof chart.resize === 'function') chart.resize()
	}

	function dispose() {
		if (_touchCleanup) _touchCleanup()
		if (chart) { chart.dispose(); chart = null }
	}

	onBeforeUnmount(() => dispose())
	return { loading, render, resize, dispose }
}

<template>
	<view class="uni-container">
		<!-- 参数设置区 -->
		<view class="param-section">
			<text class="section-title">参数设置</text>
			<view class="param-row-vertical">
				<text class="param-label">ETF标的</text>
				<view class="etf-tags">
					<view class="etf-tag" v-for="(item, index) in etfList" :key="item.code">
						<text class="etf-tag-text">{{ item.name || item.code }}</text>
						<text class="etf-tag-code">{{ item.code }}</text>
						<text class="etf-tag-remove" @click="removeEtf(index)">×</text>
					</view>
				</view>
				<view class="etf-add-row">
					<input class="param-input etf-add-input" v-model="newEtfCode"
						placeholder="输入ETF代码" @confirm="addEtf" />
					<button class="etf-add-btn" type="primary" size="mini" @click="addEtf"
						:loading="nameLoading">添加</button>
				</view>
			</view>
			<view class="param-row">
				<text class="param-label">回测期间</text>
				<view class="date-range">
					<picker mode="date" :value="startDate" @change="onStartDateChange">
						<view class="param-input date-input">{{ startDate }}</view>
					</picker>
					<text class="date-sep">~</text>
					<picker mode="date" :value="endDate" @change="onEndDateChange">
						<view class="param-input date-input">{{ endDate }}</view>
					</picker>
				</view>
			</view>
			<view class="param-row">
				<text class="param-label">回看天数(N)</text>
				<input class="param-input" type="number" v-model="lookbackN" placeholder="1-60" />
			</view>
			<view class="param-row">
				<text class="param-label">调仓周期</text>
				<input class="param-input" type="number" v-model="rebalanceDays" placeholder="天" />
			</view>
			<view class="param-row">
				<text class="param-label">初始资金</text>
				<input class="param-input" type="number" v-model="initialCapital" />
			</view>
			<view class="btn-row">
				<button class="run-btn" type="primary" size="mini" @click="runBacktest" :loading="loading">
					开始回测
				</button>
				<button class="run-btn optimize-btn" type="default" size="mini" @click="runOptimize" :loading="optimizing">
					参数优化
				</button>
			</view>
		</view>

		<!-- 参数优化结果 -->
		<view v-if="hasOptResult" class="result-section">
			<view class="chart-section">
				<text class="section-title">参数优化结果</text>
				<view class="opt-best">
					<text class="opt-best-label">最优组合：</text>
					<text class="opt-best-value">回看 {{ optBest.lookback_n }} 天 / 调仓 {{ optBest.rebalance_days }} 天</text>
					<text class="opt-best-sharpe">夏普 {{ optBest.sharpe_ratio }}</text>
					<text class="opt-best-return" :class="optBest.total_return >= 0 ? 'profit-up' : 'profit-down'">
						收益 {{ (optBest.total_return * 100).toFixed(2) }}%
					</text>
				</view>
				<button class="apply-btn" type="warn" size="mini" @click="applyBest">应用最优参数</button>
				<view id="optimize-chart" class="chart-container"></view>
			</view>
		</view>

		<!-- 回测结果区 -->
		<view v-if="hasResult" class="result-section">
			<!-- 汇总信息 -->
			<view class="summary-card">
				<view class="summary-item">
					<text class="summary-label">初始资金</text>
					<text class="summary-value">{{ formatMoney(summary.initial_capital) }}</text>
				</view>
				<view class="summary-item">
					<text class="summary-label">最终权益</text>
					<text class="summary-value">{{ formatMoney(summary.final_equity) }}</text>
				</view>
				<view class="summary-item">
					<text class="summary-label">总收益率</text>
					<text class="summary-value" :class="summary.total_return >= 0 ? 'positive' : 'negative'">
						{{ (summary.total_return * 100).toFixed(2) }}%
					</text>
				</view>
				<view class="summary-item">
					<text class="summary-label">夏普比率</text>
					<text class="summary-value">{{ summary.sharpe_ratio }}</text>
				</view>
				<view class="summary-item">
					<text class="summary-label">交易次数</text>
					<text class="summary-value">{{ summary.total_trades }}</text>
				</view>
			</view>

			<!-- 动量评分曲线 -->
			<view class="chart-section">
				<text class="section-title">动量评分曲线</text>
				<view id="momentum-chart" class="chart-container"></view>
			</view>

			<!-- 资金增长曲线 -->
			<view class="chart-section">
				<text class="section-title">资金增长曲线</text>
				<view id="equity-chart" class="chart-container"></view>
			</view>

			<!-- 交易记录 -->
			<view class="chart-section">
				<text class="section-title">交易记录</text>
				<view class="trade-list">
					<view v-if="tradeRecords.length === 0" class="trade-empty">无交易记录</view>
					<view v-for="(item, index) in tradeRecords" :key="index" class="trade-card">
						<view class="trade-row1">
							<text class="trade-etf">{{ etfLabel(item.etfCode) }}</text>
							<text class="trade-reason">{{ item.reason }}</text>
							<text class="trade-profit" :class="item.profitRate >= 0 ? 'profit-up' : 'profit-down'">
								{{ (item.profitRate >= 0 ? '+' : '') }}{{ (item.profitRate * 100).toFixed(2) }}%
							</text>
						</view>
						<view class="trade-row2">
							<view class="trade-side">
								<text class="trade-label">买入</text>
								<text class="trade-date">{{ item.buyDate }}</text>
								<text class="trade-price">{{ item.buyPrice }}</text>
							</view>
							<view class="trade-arrow">→</view>
							<view class="trade-side">
								<text class="trade-label">卖出</text>
								<text class="trade-date">{{ item.sellDate }}</text>
								<text class="trade-price">{{ item.sellPrice }}</text>
							</view>
						</view>
						</view>
					<!-- 当前持仓 -->
					<view v-if="currentHolding" class="holding-card">
						<view class="trade-row1">
							<text class="trade-etf">{{ etfLabel(currentHolding.etfCode) }}</text>
							<text class="holding-badge">持仓中</text>
							<text class="trade-profit" :class="currentHolding.unrealizedProfit >= 0 ? 'profit-up' : 'profit-down'">
								{{ (currentHolding.unrealizedProfit >= 0 ? '+' : '') }}{{ (currentHolding.unrealizedProfit * 100).toFixed(2) }}%
							</text>
						</view>
						<view class="trade-row2">
							<view class="trade-side">
								<text class="trade-label">买入日</text>
								<text class="trade-date">{{ currentHolding.buyDate }}</text>
								<text class="trade-price">{{ currentHolding.buyPrice }}</text>
							</view>
							<view class="trade-arrow">→</view>
							<view class="trade-side">
								<text class="trade-label">现价</text>
								<text class="trade-date">持有 {{ currentHolding.holdingDays }} 天</text>
								<text class="trade-price">{{ currentHolding.currentPrice }}</text>
							</view>
						</view>
					</view>
				</view>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref, nextTick, onMounted, onBeforeUnmount } from 'vue'
import getMomentumBacktest from '@/services/strategy/momentumBacktest.js'
import getMomentumOptimize from '@/services/strategy/momentumOptimize.js'
import etfNameLookup from '@/services/strategy/etfNameLookup.js'

// 参数
const etfList = ref([
	{ code: '518880', name: '' },
	{ code: '513100', name: '' },
	{ code: '510300', name: '' },
	{ code: '159915', name: '' },
])
const newEtfCode = ref('')
const nameLoading = ref(false)
const startDate = ref('2024-01-01')
const endDate = ref(new Date().toISOString().slice(0, 10))
const lookbackN = ref(25)
const rebalanceDays = ref(5)
const initialCapital = ref(1000000)
const loading = ref(false)

// 结果
const hasResult = ref(false)
const summary = ref({})
const tradeRecords = ref([])
const currentHolding = ref(null)
const etfNames = ref({})  // {code: name}

// 根据代码获取显示名称
const etfLabel = (code) => {
	const name = etfNames.value[code]
	return name && name !== code ? `${name}` : code
}

// 优化结果
const optimizing = ref(false)
const hasOptResult = ref(false)
const optBest = ref({})
const optResults = ref([])

// 图表实例
let momentumChart = null
let equityChart = null
let optimizeChart = null

const ETF_COLORS = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#fc8452']

// 页面加载时获取初始ETF名称
onMounted(async () => {
	const codes = etfList.value.map(e => e.code).join(',')
	const names = await etfNameLookup(codes)
	etfList.value.forEach(item => {
		if (names[item.code]) item.name = names[item.code]
	})
})

const removeEtf = (index) => {
	if (etfList.value.length <= 2) {
		uni.showToast({ title: '至少保留2个标的', icon: 'none' })
		return
	}
	etfList.value.splice(index, 1)
}

const addEtf = async () => {
	const code = newEtfCode.value.trim()
	if (!code) return
	if (!/^\d{6}$/.test(code)) {
		uni.showToast({ title: '请输入6位数字代码', icon: 'none' })
		return
	}
	if (etfList.value.some(e => e.code === code)) {
		uni.showToast({ title: '该标的已存在', icon: 'none' })
		return
	}

	nameLoading.value = true
	try {
		const names = await etfNameLookup(code)
		const name = names[code] || code
		etfList.value.push({ code, name })
		newEtfCode.value = ''
	} finally {
		nameLoading.value = false
	}
}

const onStartDateChange = (e) => {
	startDate.value = e.detail.value
}

const onEndDateChange = (e) => {
	endDate.value = e.detail.value
}

const formatMoney = (val) => {
	if (!val) return '0'
	return Number(val).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

const shortDate = (d) => {
	if (!d) return ''
	// YYYY/MM/DD -> MM/DD
	const parts = d.split('/')
	return parts.length === 3 ? `${parts[1]}/${parts[2]}` : d
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

async function runOptimize() {
	optimizing.value = true
	try {
		const formattedStart = startDate.value.replace(/-/g, '/')
		const formattedEnd = endDate.value.replace(/-/g, '/')

		const res = await getMomentumOptimize({
			codes: etfList.value.map(e => e.code).join(','),
			start_date: formattedStart,
			end_date: formattedEnd,
			initial_capital: initialCapital.value,
		})

		if (res.code !== 0) {
			uni.showToast({ title: res.message || '优化失败', icon: 'none' })
			return
		}

		optResults.value = res.data.results || []
		optBest.value = res.data.best || {}
		hasOptResult.value = true

		await nextTick()
		const echarts = await loadEcharts()
		renderOptimizeChart(echarts, res.data)
	} catch (e) {
		console.error('优化失败', e)
		uni.showToast({ title: '参数优化请求失败', icon: 'none' })
	} finally {
		optimizing.value = false
	}
}

function renderOptimizeChart(echarts, data) {
	if (optimizeChart) { optimizeChart.dispose(); optimizeChart = null }
	const dom = document.getElementById('optimize-chart')
	if (!dom) return

	optimizeChart = echarts.init(dom)
	const results = data.results || []
	const nList = data.n_list || []
	const rList = data.r_list || []

	// 构建热力图数据: [rIndex, nIndex, sharpe]
	const heatData = []
	let minVal = Infinity, maxVal = -Infinity
	for (const row of results) {
		const ni = nList.indexOf(row.lookback_n)
		const ri = rList.indexOf(row.rebalance_days)
		if (ni >= 0 && ri >= 0) {
			heatData.push([ni, ri, row.sharpe_ratio])
			minVal = Math.min(minVal, row.sharpe_ratio)
			maxVal = Math.max(maxVal, row.sharpe_ratio)
		}
	}

	optimizeChart.setOption({
		tooltip: {
			position: 'top',
			formatter: (p) => {
				const n = nList[p.value[0]]
				const r = rList[p.value[1]]
				const sharpe = p.value[2]
				const row = results.find(x => x.lookback_n === n && x.rebalance_days === r)
				const ret = row ? (row.total_return * 100).toFixed(2) + '%' : '-'
				return `回看 ${n}天 / 调仓 ${r}天<br/>夏普: ${sharpe}<br/>收益: ${ret}`
			}
		},
		grid: { left: '15%', right: '12%', top: 10, bottom: 60 },
		xAxis: {
			type: 'category',
			data: nList.map(n => n + '天'),
			name: '回看天数',
			nameLocation: 'center',
			nameGap: 35,
			splitArea: { show: true },
		},
		yAxis: {
			type: 'category',
			data: rList.map(r => r + '天'),
			name: '调仓周期',
			splitArea: { show: true },
		},
		visualMap: {
			min: minVal,
			max: maxVal,
			calculable: true,
			orient: 'vertical',
			right: '2%',
			top: 'center',
			itemHeight: 120,
			inRange: {
				color: ['#d94e5d', '#eac736', '#50a3ba']
			},
			textStyle: { fontSize: 10 },
		},
		series: [{
			type: 'heatmap',
			data: heatData,
			label: {
				show: true,
				formatter: (p) => p.value[2].toFixed(2),
				fontSize: 11,
			},
			emphasis: {
				itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' }
			},
		}],
	})
}

const applyBest = () => {
	if (optBest.value) {
		lookbackN.value = optBest.value.lookback_n
		rebalanceDays.value = optBest.value.rebalance_days
		uni.showToast({ title: '已应用最优参数', icon: 'success' })
	}
}

async function runBacktest() {
	loading.value = true
	try {
		// 日期格式转换: YYYY-MM-DD -> YYYY/MM/DD
		const formattedStart = startDate.value.replace(/-/g, '/')
		const formattedEnd = endDate.value.replace(/-/g, '/')

		const res = await getMomentumBacktest({
			codes: etfList.value.map(e => e.code).join(','),
			start_date: formattedStart,
			end_date: formattedEnd,
			lookback_n: lookbackN.value,
			rebalance_days: rebalanceDays.value,
			initial_capital: initialCapital.value,
		})

		if (res.code !== 0) {
			uni.showToast({ title: res.message || '回测失败', icon: 'none' })
			return
		}

		const data = res.data
		summary.value = data.summary || {}
		tradeRecords.value = data.trade_records || []
		currentHolding.value = data.current_holding || null
		etfNames.value = data.etf_names || {}
		hasResult.value = true

		await nextTick()
		const echarts = await loadEcharts()
		renderMomentumChart(echarts, data.momentum_curves)
		renderEquityChart(echarts, data.equity_curve)
	} catch (e) {
		console.error('回测失败', e)
		uni.showToast({ title: '回测请求失败', icon: 'none' })
	} finally {
		loading.value = false
	}
}

function renderMomentumChart(echarts, momentumCurves) {
	if (momentumChart) { momentumChart.dispose(); momentumChart = null }
	const dom = document.getElementById('momentum-chart')
	if (!dom) return

	momentumChart = echarts.init(dom)
	const codes = Object.keys(momentumCurves)
	const legendNames = codes.map(c => etfLabel(c))

	// 所有ETF共享同一个日期轴
	const dates = momentumCurves[codes[0]].map(item => item[0])
	const series = codes.map((code, i) => ({
		name: etfLabel(code),
		type: 'line',
		data: momentumCurves[code].map(item => item[1]),
		smooth: true,
		showSymbol: false,
		lineStyle: { width: 1.5 },
		itemStyle: { color: ETF_COLORS[i % ETF_COLORS.length] },
	}))

	// 添加零线
	series.push({
		name: '零线',
		type: 'line',
		data: dates.map(() => 0),
		showSymbol: false,
		lineStyle: { width: 1, type: 'dashed', color: '#999' },
		tooltip: { show: false },
	})

	momentumChart.setOption({
		tooltip: { trigger: 'axis' },
		legend: { data: legendNames, top: 0 },
		grid: { left: '10%', right: '4%', top: 40, bottom: 60 },
		xAxis: { type: 'category', data: dates, boundaryGap: false },
		yAxis: { type: 'value', scale: true },
		dataZoom: [
			{ type: 'inside', start: 0, end: 100 },
			{ type: 'slider', bottom: 5, start: 0, end: 100 },
		],
		series,
	})
}

function renderEquityChart(echarts, equityCurve) {
	if (equityChart) { equityChart.dispose(); equityChart = null }
	const dom = document.getElementById('equity-chart')
	if (!dom) return

	equityChart = echarts.init(dom)
	const dates = equityCurve.map(item => item[0])
	const values = equityCurve.map(item => item[1])

	equityChart.setOption({
		tooltip: {
			trigger: 'axis',
			formatter: (params) => {
				const p = params[0]
				return `${p.axisValue}<br/>资金: ${(p.value / 10000).toFixed(2)}万`
			}
		},
		grid: { left: '12%', right: '4%', top: 20, bottom: 60 },
		xAxis: { type: 'category', data: dates, boundaryGap: false },
		yAxis: {
			type: 'value',
			scale: true,
			axisLabel: {
				formatter: (val) => (val / 10000).toFixed(1) + '万'
			}
		},
		dataZoom: [
			{ type: 'inside', start: 0, end: 100 },
			{ type: 'slider', bottom: 5, start: 0, end: 100 },
		],
		series: [{
			name: '资金',
			type: 'line',
			data: values,
			smooth: true,
			showSymbol: false,
			areaStyle: { opacity: 0.15 },
			lineStyle: { width: 2, color: '#5470c6' },
			itemStyle: { color: '#5470c6' },
		}],
	})
}

// 窗口resize
function onResize() {
	momentumChart && momentumChart.resize()
	equityChart && equityChart.resize()
	optimizeChart && optimizeChart.resize()
}

if (typeof window !== 'undefined') {
	window.addEventListener('resize', onResize)
}

onBeforeUnmount(() => {
	if (typeof window !== 'undefined') {
		window.removeEventListener('resize', onResize)
	}
	if (momentumChart) { momentumChart.dispose(); momentumChart = null }
	if (equityChart) { equityChart.dispose(); equityChart = null }
	if (optimizeChart) { optimizeChart.dispose(); optimizeChart = null }
})
</script>

<style>
.uni-container {
	padding: 12px;
}

.param-section {
	background: #fff;
	border-radius: 8px;
	padding: 16px;
	margin-bottom: 12px;
	box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.section-title {
	font-size: 16px;
	font-weight: 600;
	color: #333;
	margin-bottom: 12px;
	display: block;
}

.param-row {
	display: flex;
	align-items: center;
	margin-bottom: 10px;
}

.param-label {
	width: 80px;
	font-size: 14px;
	color: #666;
	flex-shrink: 0;
}

.param-input {
	flex: 1;
	border: 1px solid #ddd;
	border-radius: 4px;
	padding: 6px 10px;
	font-size: 14px;
	max-width: 200px;
}

.param-input.wide {
	max-width: none;
}

.param-row-vertical {
	margin-bottom: 10px;
}

.etf-tags {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin: 8px 0;
}

.etf-tag {
	display: flex;
	align-items: center;
	gap: 4px;
	background: #e8f0fe;
	border-radius: 16px;
	padding: 4px 8px 4px 10px;
}

.etf-tag-text {
	font-size: 13px;
	color: #333;
	font-weight: 500;
}

.etf-tag-code {
	font-size: 11px;
	color: #888;
}

.etf-tag-remove {
	font-size: 16px;
	color: #999;
	margin-left: 2px;
	padding: 0 4px;
	line-height: 1;
}

.etf-add-row {
	display: flex;
	align-items: center;
	gap: 8px;
}

.etf-add-input {
	flex: 1;
}

.etf-add-btn {
	flex-shrink: 0;
}

.date-range {
	display: flex;
	align-items: center;
	flex: 1;
	gap: 6px;
}

.date-input {
	flex: 1;
	max-width: none;
	text-align: center;
}

.date-sep {
	font-size: 14px;
	color: #999;
	flex-shrink: 0;
}

.btn-row {
	display: flex;
	gap: 10px;
	margin-top: 12px;
}

.run-btn {
	flex: 1;
}

.optimize-btn {
	flex: 1;
}

.result-section {
	margin-top: 8px;
}

.summary-card {
	display: flex;
	flex-wrap: wrap;
	background: #fff;
	border-radius: 8px;
	padding: 12px 16px;
	margin-bottom: 12px;
	box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.summary-item {
	width: 50%;
	padding: 6px 0;
	display: flex;
	flex-direction: column;
}

.summary-label {
	font-size: 12px;
	color: #999;
}

.summary-value {
	font-size: 16px;
	font-weight: 600;
	color: #333;
	margin-top: 2px;
}

.chart-section {
	background: #fff;
	border-radius: 8px;
	padding: 16px;
	margin-bottom: 12px;
	box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.chart-container {
	width: 100%;
	height: 300px;
}

.trade-list {
	margin-top: 4px;
}

.trade-empty {
	text-align: center;
	color: #999;
	padding: 16px 0;
	font-size: 13px;
}

.trade-card {
	background: #f9f9f9;
	border-radius: 6px;
	margin-bottom: 8px;
	padding: 10px 12px;
}

.trade-row1 {
	display: flex;
	align-items: center;
	margin-bottom: 8px;
}

.trade-etf {
	font-size: 14px;
	font-weight: 600;
	color: #333;
	flex: 1;
}

.trade-reason {
	font-size: 11px;
	color: #999;
	margin-right: 8px;
}

.trade-profit {
	font-size: 14px;
	font-weight: bold;
}

.trade-row2 {
	display: flex;
	align-items: center;
	gap: 6px;
}

.trade-side {
	display: flex;
	flex-direction: column;
	align-items: center;
	flex: 1;
}

.trade-arrow {
	color: #aaa;
	font-size: 14px;
	flex-shrink: 0;
}

.trade-label {
	font-size: 10px;
	color: #aaa;
	margin-bottom: 2px;
}

.trade-date {
	font-size: 12px;
	color: #555;
}

.trade-price {
	font-size: 13px;
	font-weight: 500;
	color: #222;
}

.holding-card {
	background: #fffbe6;
	border: 1px solid #ffe58f;
	border-radius: 6px;
	padding: 10px 12px;
	margin-top: 4px;
}

.holding-badge {
	font-size: 11px;
	color: #fff;
	background: #faad14;
	border-radius: 10px;
	padding: 1px 8px;
	margin-right: auto;
}

.profit-up {
	color: #ec0000;
}

.profit-down {
	color: #00aa44;
}

.opt-best {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 8px;
	margin-bottom: 10px;
	padding: 10px;
	background: #f0f7ff;
	border-radius: 6px;
}

.opt-best-label {
	font-size: 13px;
	color: #666;
}

.opt-best-value {
	font-size: 14px;
	font-weight: 600;
	color: #333;
}

.opt-best-sharpe {
	font-size: 13px;
	color: #5470c6;
	font-weight: 500;
}

.opt-best-return {
	font-size: 13px;
	font-weight: 500;
}

.apply-btn {
	margin-bottom: 12px;
}
</style>

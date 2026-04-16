<template>
	<view class="uni-container">
		<!-- 公共参数 -->
		<view class="param-section">
			<text class="section-title">组合回测设置</text>
			<view class="param-row">
				<text class="param-label">回测期间</text>
				<view class="date-range">
					<picker mode="date" :value="startDate" @change="e => startDate = e.detail.value">
						<view class="param-input date-input">{{ startDate }}</view>
					</picker>
					<text class="date-sep">~</text>
					<picker mode="date" :value="endDate" @change="e => endDate = e.detail.value">
						<view class="param-input date-input">{{ endDate }}</view>
					</picker>
				</view>
			</view>
			<view class="param-row">
				<text class="param-label">总资金</text>
				<input class="param-input" type="number" v-model="initialCapital" />
			</view>
			<view class="param-row">
				<text class="param-label">策略一占比</text>
				<input class="param-input" type="digit" v-model="s1WeightPct" placeholder="0-100" />
				<text class="param-hint">%，策略二占 {{ (100 - Number(s1WeightPct)).toFixed(0) }}%</text>
			</view>
		</view>

		<!-- 策略一 -->
		<view class="param-section">
			<view class="section-title-row" @click="s1Open = !s1Open">
				<text class="section-title">策略一：{{ s1TypeLabel }}</text>
				<text class="fold-icon">{{ s1Open ? '▼' : '▶' }}</text>
			</view>
			<view v-show="s1Open">
				<view class="param-row">
					<text class="param-label">策略类型</text>
					<view class="signal-type-row">
						<text :class="['type-btn', s1Type === 'momentum' ? 'type-btn-active' : '']"
							@click="s1Type = 'momentum'">动量轮动</text>
						<text :class="['type-btn', s1Type === 'meanrev' ? 'type-btn-active' : '']"
							@click="s1Type = 'meanrev'">均值回归</text>
					</view>
				</view>
				<view class="param-row-vertical">
					<text class="param-label">ETF标的</text>
					<view class="etf-tags">
						<view class="etf-tag" v-for="(item, index) in s1Etfs" :key="item.code">
							<text class="etf-tag-text">{{ item.name || item.code }}</text>
							<text class="etf-tag-code">{{ item.code }}</text>
							<text class="etf-tag-remove" @click="removeEtf('s1', index)">x</text>
						</view>
					</view>
					<view class="etf-add-row">
						<input class="param-input etf-add-input" v-model="s1NewCode"
							placeholder="输入ETF代码" @confirm="addEtf('s1')" />
						<button class="etf-add-btn" type="primary" size="mini"
							@click="addEtf('s1')">添加</button>
					</view>
				</view>
				<!-- 动量参数 -->
				<template v-if="s1Type === 'momentum'">
					<view class="param-row">
						<text class="param-label">回看天数</text>
						<input class="param-input" type="number" v-model="s1MomLookback" />
						<text class="param-hint">1-60，推荐25</text>
					</view>
					<view class="param-row">
						<text class="param-label">调仓周期</text>
						<input class="param-input" type="number" v-model="s1MomRebalance" />
						<text class="param-hint">1-10天，推荐5</text>
					</view>
				</template>
				<!-- 均值回归参数 -->
				<template v-if="s1Type === 'meanrev'">
					<view class="param-row">
						<text class="param-label">信号类型</text>
						<view class="signal-type-row">
							<text :class="['type-btn', s1MrSignal === 'bollinger' ? 'type-btn-active' : '']"
								@click="s1MrSignal = 'bollinger'">布林带</text>
							<text :class="['type-btn', s1MrSignal === 'rsi' ? 'type-btn-active' : '']"
								@click="s1MrSignal = 'rsi'">RSI</text>
						</view>
					</view>
					<view class="param-row">
						<text class="param-label">指标周期</text>
						<input class="param-input" type="number" v-model="s1MrPeriod" />
						<text class="param-hint">{{ s1MrSignal === 'rsi' ? '推荐14' : '推荐20' }}</text>
					</view>
					<view v-if="s1MrSignal === 'bollinger'" class="param-row">
						<text class="param-label">标准差倍数</text>
						<input class="param-input" type="digit" v-model="s1MrStd" />
						<text class="param-hint">推荐2.0</text>
					</view>
					<view v-if="s1MrSignal === 'rsi'" class="param-row">
						<text class="param-label">超跌阈值</text>
						<input class="param-input" type="number" v-model="s1MrOversold" />
						<text class="param-hint">推荐30</text>
					</view>
					<view class="param-row">
						<text class="param-label">止损比例</text>
						<input class="param-input" type="digit" v-model="s1MrStopLoss" />
						<text class="param-hint">推荐0.05</text>
					</view>
					<view class="param-row">
						<text class="param-label">调仓周期</text>
						<input class="param-input" type="number" v-model="s1MrRebalance" />
						<text class="param-hint">推荐1</text>
					</view>
				</template>
			</view>
		</view>

		<!-- 策略二 -->
		<view class="param-section">
			<view class="section-title-row" @click="s2Open = !s2Open">
				<text class="section-title">策略二：{{ s2TypeLabel }}</text>
				<text class="fold-icon">{{ s2Open ? '▼' : '▶' }}</text>
			</view>
			<view v-show="s2Open">
				<view class="param-row">
					<text class="param-label">策略类型</text>
					<view class="signal-type-row">
						<text :class="['type-btn', s2Type === 'momentum' ? 'type-btn-active' : '']"
							@click="s2Type = 'momentum'">动量轮动</text>
						<text :class="['type-btn', s2Type === 'meanrev' ? 'type-btn-active' : '']"
							@click="s2Type = 'meanrev'">均值回归</text>
					</view>
				</view>
				<view class="param-row-vertical">
					<text class="param-label">ETF标的</text>
					<view class="etf-tags">
						<view class="etf-tag" v-for="(item, index) in s2Etfs" :key="item.code">
							<text class="etf-tag-text">{{ item.name || item.code }}</text>
							<text class="etf-tag-code">{{ item.code }}</text>
							<text class="etf-tag-remove" @click="removeEtf('s2', index)">x</text>
						</view>
					</view>
					<view class="etf-add-row">
						<input class="param-input etf-add-input" v-model="s2NewCode"
							placeholder="输入ETF代码" @confirm="addEtf('s2')" />
						<button class="etf-add-btn" type="primary" size="mini"
							@click="addEtf('s2')">添加</button>
					</view>
				</view>
				<!-- 动量参数 -->
				<template v-if="s2Type === 'momentum'">
					<view class="param-row">
						<text class="param-label">回看天数</text>
						<input class="param-input" type="number" v-model="s2MomLookback" />
						<text class="param-hint">1-60，推荐25</text>
					</view>
					<view class="param-row">
						<text class="param-label">调仓周期</text>
						<input class="param-input" type="number" v-model="s2MomRebalance" />
						<text class="param-hint">1-10天，推荐5</text>
					</view>
				</template>
				<!-- 均值回归参数 -->
				<template v-if="s2Type === 'meanrev'">
					<view class="param-row">
						<text class="param-label">信号类型</text>
						<view class="signal-type-row">
							<text :class="['type-btn', s2MrSignal === 'bollinger' ? 'type-btn-active' : '']"
								@click="s2MrSignal = 'bollinger'">布林带</text>
							<text :class="['type-btn', s2MrSignal === 'rsi' ? 'type-btn-active' : '']"
								@click="s2MrSignal = 'rsi'">RSI</text>
						</view>
					</view>
					<view class="param-row">
						<text class="param-label">指标周期</text>
						<input class="param-input" type="number" v-model="s2MrPeriod" />
						<text class="param-hint">{{ s2MrSignal === 'rsi' ? '推荐14' : '推荐20' }}</text>
					</view>
					<view v-if="s2MrSignal === 'bollinger'" class="param-row">
						<text class="param-label">标准差倍数</text>
						<input class="param-input" type="digit" v-model="s2MrStd" />
						<text class="param-hint">推荐2.0</text>
					</view>
					<view v-if="s2MrSignal === 'rsi'" class="param-row">
						<text class="param-label">超跌阈值</text>
						<input class="param-input" type="number" v-model="s2MrOversold" />
						<text class="param-hint">推荐30</text>
					</view>
					<view class="param-row">
						<text class="param-label">止损比例</text>
						<input class="param-input" type="digit" v-model="s2MrStopLoss" />
						<text class="param-hint">推荐0.05</text>
					</view>
					<view class="param-row">
						<text class="param-label">调仓周期</text>
						<input class="param-input" type="number" v-model="s2MrRebalance" />
						<text class="param-hint">推荐1</text>
					</view>
				</template>
			</view>
		</view>

		<!-- 按钮 -->
		<view class="btn-row-center">
			<button class="run-btn" type="primary" @click="runCombo" :loading="loading">开始组合回测</button>
		</view>

		<!-- 回测结果 -->
		<view v-if="hasResult" class="result-section">
			<view class="bt-section-box">
				<view class="section-title-row" @click="resultOpen = !resultOpen">
					<text class="section-title">组合回测结果</text>
					<text class="fold-icon">{{ resultOpen ? '▼' : '▶' }}</text>
				</view>
				<view v-show="resultOpen">
					<!-- 三栏对比 -->
					<view class="compare-cards">
						<view class="compare-card">
							<text class="compare-title">组合</text>
							<view class="compare-metrics">
								<view class="cm"><text class="cm-l">总收益</text><text class="cm-v" :class="profitClass(comboSummary.total_return)">{{ pct(comboSummary.total_return) }}</text></view>
								<view class="cm"><text class="cm-l">年化</text><text class="cm-v" :class="profitClass(comboSummary.annualized_return)">{{ pct(comboSummary.annualized_return) }}</text></view>
								<view class="cm"><text class="cm-l">Sharpe</text><text class="cm-v">{{ fmt(comboSummary.sharpe_ratio) }}</text></view>
								<view class="cm"><text class="cm-l">最大回撤</text><text class="cm-v profit-down">{{ pctAbs(comboSummary.max_drawdown) }}</text></view>
								<view class="cm"><text class="cm-l">Calmar</text><text class="cm-v">{{ fmt(comboSummary.calmar_ratio) }}</text></view>
								<view class="cm"><text class="cm-l">胜率</text><text class="cm-v">{{ pct(comboSummary.win_rate) }}</text></view>
								<view class="cm"><text class="cm-l">交易</text><text class="cm-v">{{ comboSummary.total_trades }}</text></view>
							</view>
						</view>
						<view class="compare-card compare-sub">
							<text class="compare-title">{{ s1Label }}（{{ Math.round(s1Weight * 100) }}%）</text>
							<view class="compare-metrics">
								<view class="cm"><text class="cm-l">总收益</text><text class="cm-v" :class="profitClass(s1Summary.total_return)">{{ pct(s1Summary.total_return) }}</text></view>
								<view class="cm"><text class="cm-l">Sharpe</text><text class="cm-v">{{ fmt(s1Summary.sharpe_ratio) }}</text></view>
								<view class="cm"><text class="cm-l">回撤</text><text class="cm-v profit-down">{{ pctAbs(s1Summary.max_drawdown) }}</text></view>
								<view class="cm"><text class="cm-l">交易</text><text class="cm-v">{{ s1Summary.total_trades }}</text></view>
							</view>
						</view>
						<view class="compare-card compare-sub">
							<text class="compare-title">{{ s2Label }}（{{ Math.round(s2Weight * 100) }}%）</text>
							<view class="compare-metrics">
								<view class="cm"><text class="cm-l">总收益</text><text class="cm-v" :class="profitClass(s2Summary.total_return)">{{ pct(s2Summary.total_return) }}</text></view>
								<view class="cm"><text class="cm-l">Sharpe</text><text class="cm-v">{{ fmt(s2Summary.sharpe_ratio) }}</text></view>
								<view class="cm"><text class="cm-l">回撤</text><text class="cm-v profit-down">{{ pctAbs(s2Summary.max_drawdown) }}</text></view>
								<view class="cm"><text class="cm-l">交易</text><text class="cm-v">{{ s2Summary.total_trades }}</text></view>
							</view>
						</view>
					</view>

					<!-- 净值曲线 -->
					<view class="chart-section">
						<text class="section-title">净值曲线</text>
						<view id="combo-equity-chart" class="chart-container"></view>
					</view>

					<!-- 交易记录 -->
					<view class="chart-section">
						<text class="section-title">交易记录</text>
						<view class="trade-list">
							<view v-if="tradeRecords.length === 0" class="trade-empty">无交易记录</view>
							<view v-for="(item, index) in tradeRecords" :key="index" class="trade-card">
								<view class="trade-row1">
									<text class="trade-strategy-badge" :class="item.strategy === s1Label ? 'badge-s1' : 'badge-s2'">{{ item.strategy }}</text>
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
									<view class="trade-arrow">-></view>
									<view class="trade-side">
										<text class="trade-label">卖出</text>
										<text class="trade-date">{{ item.sellDate }}</text>
										<text class="trade-price">{{ item.sellPrice }}</text>
									</view>
								</view>
							</view>
						</view>
					</view>
				</view>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import postComboBacktest from '@/services/strategy/comboBacktest.js'
import etfNameLookup from '@/services/strategy/etfNameLookup.js'
import userStore from '@/stores/user.js'
import { handleVipBlocked } from '@/utils/vipTip.js'

// 公共参数
const startDate = ref('2024-01-01')
const endDate = ref(new Date().toISOString().slice(0, 10))
const initialCapital = ref(1000000)
const s1WeightPct = ref(50)

// 策略一
const s1Open = ref(true)
const s1Type = ref('momentum')
const s1Etfs = ref([
	{ code: '518880', name: '' },
	{ code: '513100', name: '' },
	{ code: '510300', name: '' },
	{ code: '159915', name: '' },
])
const s1NewCode = ref('')
// 动量参数
const s1MomLookback = ref(25)
const s1MomRebalance = ref(5)
// 均值回归参数
const s1MrSignal = ref('bollinger')
const s1MrPeriod = ref(20)
const s1MrStd = ref(2.0)
const s1MrOversold = ref(30)
const s1MrStopLoss = ref(0.05)
const s1MrRebalance = ref(1)

// 策略二
const s2Open = ref(true)
const s2Type = ref('meanrev')
const s2Etfs = ref([
	{ code: '518880', name: '' },
	{ code: '513100', name: '' },
	{ code: '510300', name: '' },
	{ code: '159915', name: '' },
])
const s2NewCode = ref('')
const s2MomLookback = ref(25)
const s2MomRebalance = ref(5)
const s2MrSignal = ref('bollinger')
const s2MrPeriod = ref(20)
const s2MrStd = ref(2.0)
const s2MrOversold = ref(30)
const s2MrStopLoss = ref(0.05)
const s2MrRebalance = ref(1)

const loading = ref(false)
const hasResult = ref(false)
const resultOpen = ref(true)

const comboSummary = ref({})
const s1Summary = ref({})
const s2Summary = ref({})
const s1Label = ref('动量')
const s2Label = ref('均值回归')
const s1Weight = ref(0.5)
const s2Weight = ref(0.5)
const tradeRecords = ref([])
const etfNames = ref({})

let equityChart = null

const s1TypeLabel = computed(() => s1Type.value === 'momentum' ? '动量轮动' : '均值回归')
const s2TypeLabel = computed(() => s2Type.value === 'momentum' ? '动量轮动' : '均值回归')

const etfLabel = (code) => {
	const name = etfNames.value[code]
	return name && name !== code ? name : code
}

onMounted(async () => {
	const allCodes = [...new Set([
		...s1Etfs.value.map(e => e.code),
		...s2Etfs.value.map(e => e.code),
	])]
	const missing = allCodes.filter(c => !s1Etfs.value.find(e => e.code === c && e.name) &&
		!s2Etfs.value.find(e => e.code === c && e.name))
	if (missing.length > 0) {
		const names = await etfNameLookup(missing.join(','))
		;[s1Etfs, s2Etfs].forEach(list => {
			list.value.forEach(item => {
				if (!item.name && names[item.code]) item.name = names[item.code]
			})
		})
	}
})

const requireLogin = () => {
	if (userStore.isLoggedIn.value) return true
	uni.showModal({
		title: '需要登录',
		content: '回测功能需要先登录，是否前往登录？',
		confirmText: '去登录',
		success: (r) => {
			if (r.confirm) uni.navigateTo({ url: '/pages/auth/login' })
		},
	})
	return false
}

function getEtfState(which) {
	return which === 's1'
		? { list: s1Etfs, codeRef: s1NewCode }
		: { list: s2Etfs, codeRef: s2NewCode }
}

const removeEtf = (which, index) => {
	const { list } = getEtfState(which)
	if (list.value.length <= 2) {
		uni.showToast({ title: '至少保留2个标的', icon: 'none' })
		return
	}
	list.value.splice(index, 1)
}

const addEtf = async (which) => {
	const { list, codeRef } = getEtfState(which)
	const code = codeRef.value.trim()
	if (!code) return
	if (!/^\d{6}$/.test(code)) {
		uni.showToast({ title: '请输入6位数字代码', icon: 'none' })
		return
	}
	if (list.value.some(e => e.code === code)) {
		uni.showToast({ title: '该标的已存在', icon: 'none' })
		return
	}
	const names = await etfNameLookup(code)
	list.value.push({ code, name: names[code] || code })
	codeRef.value = ''
}

function buildStrategyParams(type, opts) {
	if (type === 'momentum') {
		return {
			lookback_n: Number(opts.lookback),
			rebalance_days: Number(opts.rebalance),
		}
	}
	return {
		signal_type: opts.signal,
		period: Number(opts.period),
		num_std: Number(opts.std),
		oversold: Number(opts.oversold),
		stop_loss: Number(opts.stopLoss),
		rebalance_days: Number(opts.rebalance),
	}
}

async function runCombo() {
	if (!requireLogin()) return
	loading.value = true
	try {
		const formattedStart = startDate.value.replace(/-/g, '/')
		const formattedEnd = endDate.value.replace(/-/g, '/')
		const w = Number(s1WeightPct.value) / 100

		const body = {
			start_date: formattedStart,
			end_date: formattedEnd,
			initial_capital: Number(initialCapital.value),
			s1_weight: w,
			s1_type: s1Type.value,
			s1_codes: s1Etfs.value.map(e => e.code),
			s1_params: buildStrategyParams(s1Type.value, {
				lookback: s1MomLookback.value, rebalance: s1Type.value === 'momentum' ? s1MomRebalance.value : s1MrRebalance.value,
				signal: s1MrSignal.value, period: s1MrPeriod.value, std: s1MrStd.value,
				oversold: s1MrOversold.value, stopLoss: s1MrStopLoss.value,
			}),
			s2_type: s2Type.value,
			s2_codes: s2Etfs.value.map(e => e.code),
			s2_params: buildStrategyParams(s2Type.value, {
				lookback: s2MomLookback.value, rebalance: s2Type.value === 'momentum' ? s2MomRebalance.value : s2MrRebalance.value,
				signal: s2MrSignal.value, period: s2MrPeriod.value, std: s2MrStd.value,
				oversold: s2MrOversold.value, stopLoss: s2MrStopLoss.value,
			}),
		}

		const res = await postComboBacktest(body)

		if (handleVipBlocked(res)) return

		if (res.code !== 0) {
			uni.showToast({ title: res.message || '回测失败', icon: 'none' })
			return
		}

		const data = res.data
		comboSummary.value = data.combo_summary || {}
		s1Summary.value = data.s1_summary || {}
		s2Summary.value = data.s2_summary || {}
		s1Label.value = data.s1_label || '策略一'
		s2Label.value = data.s2_label || '策略二'
		s1Weight.value = data.s1_weight
		s2Weight.value = data.s2_weight
		tradeRecords.value = data.trade_records || []
		etfNames.value = data.etf_names || {}
		hasResult.value = true

		await nextTick()
		const echarts = await loadEcharts()
		renderEquityChart(echarts, data.combo_equity_curve, data.s1_equity_curve, data.s2_equity_curve)
	} catch (e) {
		console.error('组合回测失败', e)
		uni.showToast({ title: '回测请求失败', icon: 'none' })
	} finally {
		loading.value = false
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

function renderEquityChart(echarts, comboCurve, s1Curve, s2Curve) {
	if (equityChart) { equityChart.dispose(); equityChart = null }
	const dom = document.getElementById('combo-equity-chart')
	if (!dom) return

	equityChart = echarts.init(dom)

	const series = []
	if (comboCurve && comboCurve.length) {
		series.push({
			name: '组合',
			type: 'line',
			data: comboCurve.map(it => [it[0], it[1]]),
			showSymbol: false,
			smooth: true,
			lineStyle: { width: 2.5, color: '#5470c6' },
			itemStyle: { color: '#5470c6' },
		})
	}
	if (s1Curve && s1Curve.length) {
		series.push({
			name: s1Label.value,
			type: 'line',
			data: s1Curve.map(it => [it[0], it[1]]),
			showSymbol: false,
			smooth: true,
			lineStyle: { width: 1.5, color: '#91cc75', type: 'dashed' },
			itemStyle: { color: '#91cc75' },
		})
	}
	if (s2Curve && s2Curve.length) {
		series.push({
			name: s2Label.value,
			type: 'line',
			data: s2Curve.map(it => [it[0], it[1]]),
			showSymbol: false,
			smooth: true,
			lineStyle: { width: 1.5, color: '#fac858', type: 'dashed' },
			itemStyle: { color: '#fac858' },
		})
	}

	equityChart.setOption({
		tooltip: {
			trigger: 'axis',
			formatter: (params) => {
				const lines = params.map(p =>
					`${p.seriesName}: ${(p.value[1] / 10000).toFixed(2)}万`
				)
				return `${params[0].axisValue}<br/>${lines.join('<br/>')}`
			}
		},
		legend: { data: series.map(s => s.name), top: 0 },
		grid: { left: '12%', right: '4%', top: 40, bottom: 60 },
		xAxis: { type: 'time' },
		yAxis: {
			type: 'value',
			scale: true,
			axisLabel: { formatter: (v) => (v / 10000).toFixed(0) + '万' }
		},
		dataZoom: [
			{ type: 'inside', start: 0, end: 100 },
			{ type: 'slider', bottom: 5, start: 0, end: 100 },
		],
		series,
	})
}

function fmt(v) {
	if (v == null || isNaN(v)) return '-'
	return Number(v).toFixed(2)
}
function pct(v) {
	if (v == null || isNaN(v)) return '-'
	return (Number(v) * 100).toFixed(2) + '%'
}
function pctAbs(v) {
	if (v == null || isNaN(v)) return '-'
	return (Math.abs(Number(v)) * 100).toFixed(2) + '%'
}
function profitClass(v) {
	if (v == null) return ''
	return v >= 0 ? 'profit-up' : 'profit-down'
}

function onResize() {
	equityChart && equityChart.resize()
}
if (typeof window !== 'undefined') {
	window.addEventListener('resize', onResize)
}
onBeforeUnmount(() => {
	if (typeof window !== 'undefined') window.removeEventListener('resize', onResize)
	if (equityChart) { equityChart.dispose(); equityChart = null }
})
</script>

<style>
.uni-container {
	padding: 12px;
	padding-bottom: 20px;
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

.section-title-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	cursor: pointer;
	margin-bottom: 12px;
}

.section-title-row .section-title {
	margin-bottom: 0;
}

.fold-icon {
	font-size: 12px;
	color: #999;
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

.param-hint {
	font-size: 11px;
	color: #aaa;
	margin-left: 8px;
	flex-shrink: 0;
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

.etf-tag-text { font-size: 13px; color: #333; font-weight: 500; }
.etf-tag-code { font-size: 11px; color: #888; }
.etf-tag-remove { font-size: 16px; color: #999; margin-left: 2px; padding: 0 4px; line-height: 1; }

.etf-add-row {
	display: flex;
	align-items: center;
	gap: 8px;
}

.etf-add-input { flex: 1; }
.etf-add-btn { flex-shrink: 0; }

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

.signal-type-row {
	display: flex;
	gap: 8px;
}

.type-btn {
	font-size: 13px;
	padding: 4px 14px;
	border-radius: 14px;
	background: #f3f4f6;
	color: #666;
	cursor: pointer;
}

.type-btn-active {
	background: #5470c6;
	color: #fff;
}

.btn-row-center {
	margin: 12px 0;
}

.run-btn {
	width: 100%;
}

.result-section {
	margin-top: 8px;
}

.bt-section-box {
	background: #fff;
	border-radius: 8px;
	padding: 10px;
	margin-bottom: 8px;
	box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

/* 对比卡片 */
.compare-cards {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin-bottom: 12px;
}

.compare-card {
	flex: 1;
	min-width: 200px;
	background: #f0f5ff;
	border: 1px solid #d6e4ff;
	border-radius: 8px;
	padding: 10px;
}

.compare-sub {
	background: #fafbfc;
	border-color: #e8eaed;
}

.compare-title {
	font-size: 14px;
	font-weight: 600;
	color: #333;
	margin-bottom: 8px;
	display: block;
}

.compare-metrics {
	display: flex;
	flex-wrap: wrap;
	gap: 4px 12px;
}

.cm {
	display: flex;
	flex-direction: column;
}

.cm-l {
	font-size: 10px;
	color: #999;
}

.cm-v {
	font-size: 13px;
	font-weight: 600;
	color: #333;
}

.chart-section {
	background: #fff;
	border-radius: 8px;
	padding: 10px;
	margin-bottom: 8px;
	box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.chart-container {
	width: 100%;
	height: 300px;
}

.trade-list { margin-top: 4px; }
.trade-empty { text-align: center; color: #999; padding: 16px 0; font-size: 13px; }

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
	gap: 6px;
}

.trade-strategy-badge {
	font-size: 10px;
	padding: 1px 6px;
	border-radius: 8px;
	color: #fff;
	flex-shrink: 0;
}

.badge-s1 { background: #5470c6; }
.badge-s2 { background: #fac858; color: #333; }

.trade-etf { font-size: 14px; font-weight: 600; color: #333; flex: 1; }
.trade-reason { font-size: 11px; color: #999; }
.trade-profit { font-size: 14px; font-weight: bold; }

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

.trade-arrow { color: #aaa; font-size: 14px; flex-shrink: 0; }
.trade-label { font-size: 10px; color: #aaa; margin-bottom: 2px; }
.trade-date { font-size: 12px; color: #555; }
.trade-price { font-size: 13px; font-weight: 500; color: #222; }

.profit-up { color: #ec0000; }
.profit-down { color: #00aa44; }
</style>

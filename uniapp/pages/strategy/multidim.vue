<template>
	<view class="uni-container">
		<!-- 参数设置 -->
		<view class="param-section">
			<view class="section-title-bar">
				<text class="section-title">参数设置</text>
			</view>

			<!-- 标的 -->
			<view class="param-row-vertical">
				<text class="param-label">股票标的</text>
				<view class="stock-row">
					<etf-selector
						v-model="stockCode"
						:candidates="myWatchlist"
						placeholder="输入代码或从关注列表选择"
					/>
					<text v-if="stockName" class="stock-name">{{ stockName }}</text>
				</view>
			</view>

			<!-- 回测期间 -->
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
				<text class="param-label">初始资金</text>
				<input class="param-input" type="number" v-model="initialCapital" />
			</view>

			<view class="param-row">
				<text class="param-label">合成模式</text>
				<picker :range="combineModeLabels" :value="combineModeIndex" @change="onCombineModeChange">
					<view class="param-input date-input">{{ combineModeLabels[combineModeIndex] }}</view>
				</picker>
			</view>

			<!-- 趋势 -->
			<view class="dim-box">
				<view class="dim-header">
					<text class="dim-title">趋势</text>
					<switch :checked="trendEnabled" @change="e => trendEnabled = e.detail.value" color="#1976d2" style="transform:scale(0.7);" />
				</view>
				<text class="dim-desc">收盘价在 MA{{ trendLong }} 上方 且 MA{{ trendShort }} 在 MA{{ trendLong }} 上方</text>
				<view class="param-row">
					<text class="param-label param-label-sub">短均线</text>
					<input class="param-input" type="number" v-model="trendShort" />
					<text class="param-hint">默认 20</text>
				</view>
				<view class="param-row">
					<text class="param-label param-label-sub">长均线</text>
					<input class="param-input" type="number" v-model="trendLong" />
					<text class="param-hint">默认 60</text>
				</view>
			</view>

			<!-- 动量 -->
			<view class="dim-box">
				<view class="dim-header">
					<text class="dim-title">动量</text>
					<switch :checked="momentumEnabled" @change="e => momentumEnabled = e.detail.value" color="#1976d2" style="transform:scale(0.7);" />
				</view>
				<text class="dim-desc">过去 {{ momentumPeriod }} 日累计收益 &gt; 0</text>
				<view class="param-row">
					<text class="param-label param-label-sub">周期</text>
					<input class="param-input" type="number" v-model="momentumPeriod" />
					<text class="param-hint">默认 60</text>
				</view>
			</view>

			<!-- 量价 -->
			<view class="dim-box">
				<view class="dim-header">
					<text class="dim-title">量价</text>
					<switch :checked="volpriceEnabled" @change="e => volpriceEnabled = e.detail.value" color="#1976d2" style="transform:scale(0.7);" />
				</view>
				<text class="dim-desc">近 {{ volFlowPeriod }} 日均量 / 近 {{ volRatioPeriod }} 日均量 &gt; {{ volRatioThreshold }} 且 {{ volFlowPeriod }} 日累计资金流为正</text>
				<view class="param-row">
					<text class="param-label param-label-sub">近期窗口</text>
					<input class="param-input" type="number" v-model="volFlowPeriod" />
					<text class="param-hint">默认 5（量比分子 + 资金流窗口）</text>
				</view>
				<view class="param-row">
					<text class="param-label param-label-sub">基准窗口</text>
					<input class="param-input" type="number" v-model="volRatioPeriod" />
					<text class="param-hint">默认 20（量比分母）</text>
				</view>
				<view class="param-row">
					<text class="param-label param-label-sub">量比阈值</text>
					<input class="param-input" type="digit" v-model="volRatioThreshold" />
					<text class="param-hint">默认 0.9（近期量能不弱于基准 90%）</text>
				</view>
			</view>

			<!-- 风控 -->
			<view class="dim-box">
				<view class="dim-header">
					<text class="dim-title">风控</text>
					<switch :checked="riskEnabled" @change="e => riskEnabled = e.detail.value" color="#1976d2" style="transform:scale(0.7);" />
				</view>
				<text class="dim-desc">{{ riskModeIdx === 0
					? `距 ${riskLookback} 日高点回撤 < ${riskDrawdownPct}%`
					: `距 ${riskLookback} 日高点回撤 < (${riskAtrK} × ATR/close)，自适应波动率` }}</text>
				<view class="param-row">
					<text class="param-label param-label-sub">阈值模式</text>
					<picker :range="thresholdModeLabels" :value="riskModeIdx" @change="e => riskModeIdx = Number(e.detail.value)">
						<view class="param-input date-input">{{ thresholdModeLabels[riskModeIdx] }}</view>
					</picker>
				</view>
				<view class="param-row">
					<text class="param-label param-label-sub">回看周期</text>
					<input class="param-input" type="number" v-model="riskLookback" />
					<text class="param-hint">默认 60</text>
				</view>
				<view class="param-row" v-if="riskModeIdx === 0">
					<text class="param-label param-label-sub">回撤阈值 (%)</text>
					<input class="param-input" type="digit" v-model="riskDrawdownPct" />
					<text class="param-hint">默认 8</text>
				</view>
				<view class="param-row" v-if="riskModeIdx === 1">
					<text class="param-label param-label-sub">ATR 倍数 k</text>
					<input class="param-input" type="digit" v-model="riskAtrK" />
					<text class="param-hint">默认 2</text>
				</view>
			</view>

			<!-- 跟踪止损（独立于维度，持仓中专门保护） -->
			<view class="dim-box">
				<view class="dim-header">
					<text class="dim-title">跟踪止损</text>
					<switch :checked="trailingStopEnabled" @change="e => trailingStopEnabled = e.detail.value" color="#ec0000" style="transform:scale(0.7);" />
				</view>
				<text class="dim-desc">{{ trailModeIdx === 0
					? `从持仓后最高回落 > ${trailPct}% 时强制卖出`
					: `从持仓后最高回落 > (${trailAtrK} × ATR/close) 时强制卖出，自适应波动率` }}</text>
				<view class="param-row">
					<text class="param-label param-label-sub">幅度模式</text>
					<picker :range="trailModeLabels" :value="trailModeIdx" @change="e => trailModeIdx = Number(e.detail.value)">
						<view class="param-input date-input">{{ trailModeLabels[trailModeIdx] }}</view>
					</picker>
				</view>
				<view class="param-row" v-if="trailModeIdx === 0">
					<text class="param-label param-label-sub">回落幅度 (%)</text>
					<input class="param-input" type="digit" v-model="trailPct" />
					<text class="param-hint">默认 10</text>
				</view>
				<view class="param-row" v-if="trailModeIdx === 1">
					<text class="param-label param-label-sub">ATR 倍数 k</text>
					<input class="param-input" type="digit" v-model="trailAtrK" />
					<text class="param-hint">默认 3</text>
				</view>
			</view>

			<!-- ATR 共享设置：风控和止损共用同一个 ATR 周期（仅至少一处选 ATR 模式时显示） -->
			<view class="dim-box dim-box-shared" v-if="riskModeIdx === 1 || trailModeIdx === 1">
				<view class="dim-header">
					<text class="dim-title">ATR 共享设置</text>
				</view>
				<text class="dim-desc">风控和跟踪止损在 ATR 模式下共用同一个 ATR 序列</text>
				<view class="param-row">
					<text class="param-label param-label-sub">ATR 周期</text>
					<input class="param-input" type="number" v-model="atrPeriod" />
					<text class="param-hint">默认 14</text>
				</view>
			</view>

			<!-- 市场过滤（独立 gate，仅过滤新开仓） -->
			<view class="dim-box">
				<view class="dim-header">
					<text class="dim-title">市场过滤</text>
					<switch :checked="marketFilterEnabled" @change="e => marketFilterEnabled = e.detail.value" color="#1976d2" style="transform:scale(0.7);" />
				</view>
				<text class="dim-desc">{{ marketIndexLabels[marketIndexIdx] }} 在 MA{{ marketMaPeriod }} 上方时才允许新开仓</text>
				<view class="param-row">
					<text class="param-label param-label-sub">参考指数</text>
					<picker :range="marketIndexLabels" :value="marketIndexIdx" @change="onMarketIndexChange">
						<view class="param-input date-input">{{ marketIndexLabels[marketIndexIdx] }}</view>
					</picker>
				</view>
				<view class="param-row">
					<text class="param-label param-label-sub">MA 周期</text>
					<input class="param-input" type="number" v-model="marketMaPeriod" />
					<text class="param-hint">默认 60</text>
				</view>
			</view>

			<view class="btn-row">
				<button class="run-btn" type="primary" size="mini" @click="runBacktest" :loading="loading">
					开始回测
				</button>
			</view>
		</view>

		<!-- 回测结果 -->
		<view v-if="hasResult" class="result-section">
			<!-- summary -->
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
					<text class="summary-label">年化收益</text>
					<text class="summary-value" :class="(summary.annualized_return || 0) >= 0 ? 'positive' : 'negative'">
						{{ ((summary.annualized_return || 0) * 100).toFixed(2) }}%
					</text>
				</view>
				<view class="summary-item">
					<text class="summary-label">夏普比率</text>
					<text class="summary-value">{{ summary.sharpe_ratio }}</text>
				</view>
				<view class="summary-item">
					<text class="summary-label">最大回撤</text>
					<text class="summary-value negative">
						{{ (Math.abs(summary.max_drawdown || 0) * 100).toFixed(2) }}%
					</text>
				</view>
				<view class="summary-item">
					<text class="summary-label">胜率</text>
					<text class="summary-value">{{ ((summary.win_rate || 0) * 100).toFixed(1) }}%</text>
				</view>
				<view class="summary-item">
					<text class="summary-label">交易次数</text>
					<text class="summary-value">{{ summary.total_trades }}</text>
				</view>
				<view class="summary-item">
					<text class="summary-label">基准收益</text>
					<text class="summary-value" :class="(summary.benchmark_total_return || 0) >= 0 ? 'positive' : 'negative'">
						{{ ((summary.benchmark_total_return || 0) * 100).toFixed(2) }}%
					</text>
				</view>
				<view class="summary-item">
					<text class="summary-label">基准回撤</text>
					<text class="summary-value negative">
						{{ (Math.abs(summary.benchmark_max_drawdown || 0) * 100).toFixed(2) }}%
					</text>
				</view>
				<view class="summary-item">
					<text class="summary-label">超额(α)</text>
					<text class="summary-value" :class="(summary.alpha_total_return || 0) >= 0 ? 'positive' : 'negative'">
						{{ ((summary.alpha_total_return || 0) * 100).toFixed(2) }}%
					</text>
				</view>
				<view class="summary-item">
					<text class="summary-label">年化α</text>
					<text class="summary-value" :class="(summary.alpha_annualized_return || 0) >= 0 ? 'positive' : 'negative'">
						{{ ((summary.alpha_annualized_return || 0) * 100).toFixed(2) }}%
					</text>
				</view>
				<view class="summary-item">
					<text class="summary-label">合成模式</text>
					<text class="summary-value">{{ combineModeText }}</text>
				</view>
				<view v-if="summary.trailing_stop_enabled" class="summary-item">
					<text class="summary-label">止损触发</text>
					<text class="summary-value">{{ summary.trailing_stop_exits || 0 }} 次 / {{ trailStopText }}</text>
				</view>
				<view v-if="summary.risk_enabled && summary.risk_mode === 'atr'" class="summary-item">
					<text class="summary-label">风控等效</text>
					<text class="summary-value">{{ riskEffText }}</text>
				</view>
				<view v-if="summary.market_filter_enabled" class="summary-item">
					<text class="summary-label">市场禁仓</text>
					<text class="summary-value">{{ summary.market_gate_blocked_days || 0 }} 天 / {{ summary.market_index_name || '' }}</text>
				</view>
			</view>

			<!-- 图表 -->
			<view class="chart-section">
				<view id="multidim-chart" class="chart-container chart-container-tall"></view>
			</view>

			<!-- 交易记录 -->
			<view class="chart-section">
				<text class="section-title">交易记录</text>
				<view class="trade-list">
					<view v-if="tradeRecords.length === 0" class="trade-empty">无交易记录</view>
					<view v-for="(item, index) in tradeRecords" :key="index" class="trade-card">
						<view class="trade-row1">
							<text class="trade-etf">{{ item.etfCode }}</text>
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
					<view v-if="currentHolding" class="holding-card">
						<view class="trade-row1">
							<text class="trade-etf">{{ currentHolding.etfCode }}</text>
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
							<view class="trade-arrow">-></view>
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
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import getMultidimBacktest from '@/services/strategy/multidimBacktest.js'
import { useMultidimChart } from './multidimChart.js'
import { getMy } from '@/services/sk/getMy.js'
import EtfSelector from '@/components/etf-selector/etf-selector.vue'

// ── 参数 ──
const stockCode = ref('600519')
const stockName = ref('')
const myWatchlist = ref([])  // [{code, name}] 关注列表，作为下拉候选

// 关注列表中代码 → 名称 的快速查找
function nameFromWatchlist(code) {
	const c = String(code || '').trim()
	if (!c) return ''
	const item = myWatchlist.value.find(it => it.code === c)
	return item ? (item.name || '') : ''
}

watch(stockCode, (val) => {
	const n = nameFromWatchlist(val)
	if (n) stockName.value = n
	// 不在关注列表里的代码暂留旧名称，由后端回测返回时回填
})

onMounted(async () => {
	try {
		const res = await getMy()
		if (res && res.code === 0 && res.data && Array.isArray(res.data.userSkList)) {
			myWatchlist.value = res.data.userSkList.map(it => ({
				code: it.skId,
				name: it.skName,
			}))
			// 如果当前默认 stockCode 正好在关注列表里，预填名称
			const n = nameFromWatchlist(stockCode.value)
			if (n) stockName.value = n
		}
	} catch (e) {
		// 未登录或失败时静默
	}
})
const startDate = ref('2024-01-01')
const endDate = ref(new Date().toISOString().slice(0, 10))
const initialCapital = ref(1000000)

const trendEnabled = ref(true)
const trendShort = ref(20)
const trendLong = ref(60)

const momentumEnabled = ref(true)
const momentumPeriod = ref(60)

const volpriceEnabled = ref(true)
const volRatioPeriod = ref(20)
const volRatioThreshold = ref(0.9)
const volFlowPeriod = ref(5)

const riskEnabled = ref(true)
const riskLookback = ref(60)
const riskDrawdownPct = ref(8)    // UI 以百分数显示
const thresholdModeLabels = ['固定阈值', 'ATR 自适应']
const riskModeIdx = ref(0)         // 0=fixed, 1=atr
const riskAtrK = ref(2)

// 跟踪止损
const trailingStopEnabled = ref(false)
const trailPct = ref(10)          // UI 以百分数显示
const trailModeLabels = ['固定幅度', 'ATR 自适应']
const trailModeIdx = ref(0)        // 0=fixed, 1=atr
const trailAtrK = ref(3)

// ATR 周期（共享）
const atrPeriod = ref(14)

// 市场过滤
const marketFilterEnabled = ref(false)
const marketIndexLabels = ['沪深300', '上证综指', '中证500', '中证1000', '上证50', '创业板指', '深证成指']
const marketIndexCodes  = ['000300.SH', '000001.SH', '000905.SH', '000852.SH', '000016.SH', '399006.SZ', '399001.SZ']
const marketIndexIdx = ref(0)
const marketMaPeriod = ref(60)
function onMarketIndexChange(e) { marketIndexIdx.value = Number(e.detail.value) }

// 合成模式：0=全部满足(AND)，1/2/3 = 至少 N 个
const combineModeLabels = ['全部满足', '至少 3 个', '至少 2 个', '至少 1 个']
const combineModeValues = [0, 3, 2, 1]   // 0 表示 AND（min_match_count = null）
const combineModeIndex = ref(0)
function onCombineModeChange(e) { combineModeIndex.value = Number(e.detail.value) }

// ── 结果 ──
const loading = ref(false)
const result = ref(null)
const hasResult = computed(() => !!result.value && (result.value.chart_data?.dates?.length || 0) > 0)
const summary = computed(() => result.value?.summary || {})
const tradeRecords = computed(() => result.value?.trade_records || [])
const currentHolding = computed(() => result.value?.current_holding || null)
const trailStopText = computed(() => {
	const s = summary.value
	if (s?.trail_mode === 'atr') {
		const eff = (s.trail_eff_avg != null) ? `≈${(s.trail_eff_avg * 100).toFixed(1)}%` : ''
		return `ATR×${s.trail_atr_k} ${eff}`
	}
	return `${trailPct.value}%`
})
const riskEffText = computed(() => {
	const s = summary.value
	const eff = (s?.risk_eff_avg != null) ? `≈${(s.risk_eff_avg * 100).toFixed(1)}%` : ''
	return `ATR×${s?.risk_atr_k ?? '-'} ${eff}`
})
const combineModeText = computed(() => {
	const s = summary.value
	const n = s?.n_enabled_dimensions
	const m = s?.min_match_count
	if (!n) return '-'
	if (!m || m >= n) return `全部满足 (${n}/${n})`
	return `${m}-of-${n}`
})

const { render } = useMultidimChart()

function onStartDateChange(e) { startDate.value = e.detail.value }
function onEndDateChange(e) { endDate.value = e.detail.value }

function toApiDate(d) {
	return String(d || '').replace(/-/g, '/')
}

async function runBacktest() {
	if (!stockCode.value) {
		uni.showToast({ title: '请输入股票代码', icon: 'none' })
		return
	}
	loading.value = true
	try {
		const params = {
			stock_code: stockCode.value,
			start_date: toApiDate(startDate.value),
			end_date: toApiDate(endDate.value),
			initial_capital: Number(initialCapital.value) || 1000000,
			trend_enabled: trendEnabled.value ? 1 : 0,
			trend_short_period: Number(trendShort.value) || 20,
			trend_long_period: Number(trendLong.value) || 60,
			momentum_enabled: momentumEnabled.value ? 1 : 0,
			momentum_period: Number(momentumPeriod.value) || 60,
			volprice_enabled: volpriceEnabled.value ? 1 : 0,
			volprice_ratio_period: Number(volRatioPeriod.value) || 20,
			volprice_flow_period: Number(volFlowPeriod.value) || 5,
			volprice_ratio_threshold: Number(volRatioThreshold.value) || 1.0,
			risk_enabled: riskEnabled.value ? 1 : 0,
			risk_lookback: Number(riskLookback.value) || 60,
			risk_drawdown_threshold: (Number(riskDrawdownPct.value) || 0) / 100,
			risk_mode: riskModeIdx.value === 1 ? 'atr' : 'fixed',
			risk_atr_k: Number(riskAtrK.value) || 2,
			min_match_count: combineModeValues[combineModeIndex.value],
			trailing_stop_enabled: trailingStopEnabled.value ? 1 : 0,
			trail_pct: (Number(trailPct.value) || 0) / 100,
			trail_mode: trailModeIdx.value === 1 ? 'atr' : 'fixed',
			trail_atr_k: Number(trailAtrK.value) || 3,
			atr_period: Number(atrPeriod.value) || 14,
			market_filter_enabled: marketFilterEnabled.value ? 1 : 0,
			market_index: marketIndexCodes[marketIndexIdx.value],
			market_ma_period: Number(marketMaPeriod.value) || 60,
		}
		const resp = await getMultidimBacktest(params)
		if (resp.code !== 0) {
			uni.showToast({ title: resp.message || '回测失败', icon: 'none' })
			return
		}
		result.value = resp.data
		stockName.value = resp.data.stock_name || ''
		await nextTick()
		const enabledFlags = {
			trend: trendEnabled.value,
			momentum: momentumEnabled.value,
			volprice: volpriceEnabled.value,
			risk: riskEnabled.value,
		}
		const dimensionParams = {
			trend_short: Number(trendShort.value) || 20,
			trend_long: Number(trendLong.value) || 60,
			momentum_period: Number(momentumPeriod.value) || 60,
			vol_ratio_period: Number(volRatioPeriod.value) || 20,
			vol_flow_period: Number(volFlowPeriod.value) || 5,
			vol_ratio_threshold: Number(volRatioThreshold.value) || 0.9,
			risk_drawdown: params.risk_drawdown_threshold,
		}
		await render('multidim-chart', {
			chartData: resp.data.chart_data,
			dimensionParams,
			enabledFlags,
			title: `${resp.data.stock_name || stockCode.value}（${stockCode.value}）`,
		})
	} catch (e) {
		console.error(e)
		uni.showToast({ title: '请求失败', icon: 'none' })
	} finally {
		loading.value = false
	}
}

function formatMoney(v) {
	if (!v && v !== 0) return '-'
	return Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}
</script>

<style>
.uni-container { padding: 10px; background: #f5f5f5; }

.param-section {
	background: #fff; border-radius: 8px; padding: 12px; margin-bottom: 10px;
}
.section-title-bar { display: flex; align-items: center; justify-content: space-between; padding-bottom: 8px; border-bottom: 1px solid #eee; margin-bottom: 10px; }
.section-title { font-size: 15px; font-weight: 600; color: #333; }

.param-row { display: flex; flex-direction: row; align-items: center; margin-bottom: 8px; }
.param-row-vertical { display: flex; flex-direction: column; margin-bottom: 10px; }
.param-label { width: 80px; font-size: 13px; color: #555; flex-shrink: 0; }
.param-label-sub { width: 70px; font-size: 12px; color: #777; }
.param-input { flex: 1; border: 1px solid #ddd; border-radius: 4px; padding: 4px 8px; font-size: 13px; background: #fff; }
.param-hint { font-size: 11px; color: #999; margin-left: 8px; }

.stock-row { display: flex; flex-direction: row; align-items: center; margin-top: 6px; gap: 8px; flex-wrap: wrap; }
.stock-name { font-size: 13px; color: #333; }

.date-range { flex: 1; display: flex; flex-direction: row; align-items: center; }
.date-input { text-align: center; }
.date-sep { padding: 0 6px; color: #888; }

.dim-box {
	margin-top: 10px; padding: 10px; background: #fafafa; border-radius: 6px; border: 1px solid #eee;
}
.dim-box-dim { opacity: 0.55; }
.dim-box-shared { background: #f0f4f8; border-color: #d0dae5; }
.dim-header { display: flex; flex-direction: row; align-items: center; justify-content: space-between; }
.dim-title { font-size: 14px; font-weight: 600; color: #333; }
.dim-desc { display: block; font-size: 12px; color: #888; margin: 4px 0 6px; }
.dim-desc-todo { color: #aaa; font-style: italic; }

.btn-row { display: flex; flex-direction: row; gap: 8px; margin-top: 12px; }
.run-btn { flex: 1; }

.result-section { background: #fff; border-radius: 8px; padding: 12px; margin-bottom: 10px; }

.summary-card {
	display: flex; flex-direction: row; flex-wrap: wrap;
	gap: 8px; margin-bottom: 10px;
}
.summary-item { flex: 1 1 calc(25% - 8px); min-width: 80px; display: flex; flex-direction: column; padding: 6px; background: #fafafa; border-radius: 4px; }
.summary-label { font-size: 11px; color: #888; }
.summary-value { font-size: 13px; color: #333; font-weight: 600; }
.positive { color: #ec0000; }
.negative { color: #00a040; }

.warn-tip { font-size: 12px; color: #c66; background: #fff5f5; border-left: 3px solid #e88; padding: 6px 8px; margin-bottom: 10px; border-radius: 3px; }

.chart-section { margin-top: 10px; }
.chart-container { width: 100%; height: 300px; }
.chart-container-tall { height: 620px; }

.trade-list { display: flex; flex-direction: column; gap: 8px; }
.trade-empty { color: #aaa; text-align: center; padding: 20px 0; font-size: 13px; }
.trade-card, .holding-card { background: #fafafa; border-radius: 6px; padding: 8px 10px; border: 1px solid #eee; }
.holding-card { border-color: #ffc; background: #fffbe6; }
.trade-row1 { display: flex; flex-direction: row; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.trade-row2 { display: flex; flex-direction: row; align-items: center; justify-content: space-between; font-size: 12px; color: #666; }
.trade-etf { font-size: 13px; font-weight: 600; color: #333; }
.trade-reason { font-size: 11px; color: #888; }
.trade-profit { font-size: 13px; font-weight: 600; }
.profit-up { color: #ec0000; }
.profit-down { color: #00a040; }
.trade-side { display: flex; flex-direction: column; }
.trade-label { font-size: 10px; color: #aaa; }
.trade-date { font-size: 12px; color: #666; }
.trade-price { font-size: 12px; color: #333; }
.trade-arrow { color: #aaa; padding: 0 6px; }
.holding-badge { background: #ffa200; color: #fff; font-size: 10px; padding: 1px 6px; border-radius: 8px; }
</style>

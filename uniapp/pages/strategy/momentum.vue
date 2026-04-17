<template>
	<view class="uni-container">
		<!-- 参数设置区 -->
		<view class="param-section">
			<text class="section-title">
				参数设置<p v-if="isEditMode" class="edit-banner">（{{ editingSubName }}）</p>
			</text>
			<view class="param-row-vertical">
				<text class="param-label">ETF标的</text>
				<view class="etf-tags">
					<view class="etf-tag" v-for="(item, index) in etfList" :key="item.code">
						<text class="etf-tag-text">{{ item.name || item.code }}</text>
						<text class="etf-tag-code">{{ item.code }}</text>
						<text class="etf-tag-remove" @click="removeEtf(index)">×</text>
					</view>
				</view>
				<etf-selector
					v-model="newEtfCode"
					:candidates="myWatchlist"
					:loading="nameLoading"
					@add="addEtf"
				/>
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
			<view class="param-row opt-extra-row">
				<text class="param-label">样本外验证</text>
				<switch :checked="enableOos" @change="onOosChange" color="#ffa200" style="transform:scale(0.8);" />
				<text class="opt-extra-hint">留最后 30% 数据做验证</text>
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
				<view class="section-title-row" @click="optSectionOpen = !optSectionOpen">
					<text class="section-title">参数优化结果</text>
					<text class="fold-icon">{{ optSectionOpen ? '▼' : '▶' }}</text>
				</view>

				<view v-show="optSectionOpen">
				<!-- 三张 best 卡片 -->
				<view class="best-cards">
					<view class="best-card best-card-sharpe" @click="selectByBest('sharpe')">
						<view class="best-card-head">
							<text class="best-card-title">🏆 夏普最高</text>
							<text v-if="optBestSharpe && optBestSharpe.robust === false" class="best-warn">⚠ 过拟合风险</text>
						</view>
						<text class="best-card-param" v-if="optBestSharpe">n={{ optBestSharpe.lookback_n }}  r={{ optBestSharpe.rebalance_days }}</text>
						<view v-if="optBestSharpe" class="best-card-metrics">
							<view class="best-metric"><text class="m-label">Sharpe</text><text class="m-val">{{ fmt(optBestSharpe.sharpe_ratio) }}</text></view>
							<view class="best-metric"><text class="m-label">收益</text><text class="m-val" :class="profitClass(optBestSharpe.total_return)">{{ pct(optBestSharpe.total_return) }}</text></view>
							<view class="best-metric"><text class="m-label">回撤</text><text class="m-val profit-down">{{ pctAbs(optBestSharpe.max_drawdown) }}</text></view>
						</view>
						<button class="apply-mini" type="default" size="mini" @click.stop="applyRow(optBestSharpe)">应用</button>
					</view>

					<view class="best-card best-card-robust" @click="selectByBest('robust')">
						<view class="best-card-head">
							<text class="best-card-title">🛡 稳健性最佳</text>
							<text class="best-ok">✓ 邻居一致</text>
						</view>
						<text class="best-card-param" v-if="optBestRobust">n={{ optBestRobust.lookback_n }}  r={{ optBestRobust.rebalance_days }}</text>
						<view v-if="optBestRobust" class="best-card-metrics">
							<view class="best-metric"><text class="m-label">平滑Sharpe</text><text class="m-val">{{ fmt(optBestRobust.smoothed_sharpe) }}</text></view>
							<view class="best-metric"><text class="m-label">收益</text><text class="m-val" :class="profitClass(optBestRobust.total_return)">{{ pct(optBestRobust.total_return) }}</text></view>
							<view class="best-metric"><text class="m-label">回撤</text><text class="m-val profit-down">{{ pctAbs(optBestRobust.max_drawdown) }}</text></view>
						</view>
						<button class="apply-mini" type="default" size="mini" @click.stop="applyRow(optBestRobust)">应用</button>
					</view>

					<view v-if="optHasOos" class="best-card best-card-oos" @click="selectByBest('oos')">
						<view class="best-card-head">
							<text class="best-card-title">🎯 样本外最佳</text>
							<text v-if="optBestOos" class="best-ok">{{ oosDecayLabel(optBestOos) }}</text>
						</view>
						<text class="best-card-param" v-if="optBestOos">n={{ optBestOos.lookback_n }}  r={{ optBestOos.rebalance_days }}</text>
						<view v-if="optBestOos" class="best-card-metrics">
							<view class="best-metric"><text class="m-label">OOS Sharpe</text><text class="m-val">{{ fmt(optBestOos.oos_sharpe) }}</text></view>
							<view class="best-metric"><text class="m-label">IS Sharpe</text><text class="m-val">{{ fmt(optBestOos.sharpe_ratio) }}</text></view>
							<view class="best-metric"><text class="m-label">OOS 收益</text><text class="m-val" :class="profitClass(optBestOos.oos_total_return)">{{ pct(optBestOos.oos_total_return) }}</text></view>
						</view>
						<button class="apply-mini" type="default" size="mini" @click.stop="applyRow(optBestOos)">应用</button>
					</view>
				</view>

				<!-- 热力图 Tab -->
				<view class="heatmap-tabs">
					<text :class="['heatmap-tab', heatmapMetric === 'composite' ? 'active' : '']" @click="switchHeatmap('composite')">综合得分</text>
					<text :class="['heatmap-tab', heatmapMetric === 'sharpe' ? 'active' : '']" @click="switchHeatmap('sharpe')">Sharpe</text>
					<text :class="['heatmap-tab', heatmapMetric === 'mdd' ? 'active' : '']" @click="switchHeatmap('mdd')">最大回撤</text>
					<text :class="['heatmap-tab', heatmapMetric === 'winrate' ? 'active' : '']" @click="switchHeatmap('winrate')">胜率</text>
					<text :class="['heatmap-tab', heatmapMetric === 'smoothed' ? 'active' : '']" @click="switchHeatmap('smoothed')">平滑Sharpe</text>
					<text v-if="optHasOos" :class="['heatmap-tab', heatmapMetric === 'oos' ? 'active' : '']" @click="switchHeatmap('oos')">OOS Sharpe</text>
				</view>
				<view id="optimize-chart" class="chart-container"></view>

				<!-- 详细结果表（可折叠） -->
				<view class="section-title-row sub-fold" @click="optTableOpen = !optTableOpen">
					<text class="sub-fold-label">详细数据表</text>
					<text class="fold-icon">{{ optTableOpen ? '▼' : '▶' }}</text>
				</view>
				<view v-show="optTableOpen">
					<view class="opt-table-wrap">
						<view class="opt-table-head">
							<text class="opt-th opt-th-narrow" @click="sortBy('lookback_n')">n {{ sortIcon('lookback_n') }}</text>
							<text class="opt-th opt-th-narrow" @click="sortBy('rebalance_days')">r {{ sortIcon('rebalance_days') }}</text>
							<text class="opt-th" @click="sortBy('total_return')">收益 {{ sortIcon('total_return') }}</text>
							<text class="opt-th" @click="sortBy('sharpe_ratio')">Sharpe {{ sortIcon('sharpe_ratio') }}</text>
							<text class="opt-th" @click="sortBy('smoothed_sharpe')">平滑 {{ sortIcon('smoothed_sharpe') }}</text>
							<text class="opt-th" @click="sortBy('max_drawdown')">回撤 {{ sortIcon('max_drawdown') }}</text>
							<text class="opt-th" @click="sortBy('calmar_ratio')">Calmar {{ sortIcon('calmar_ratio') }}</text>
							<text class="opt-th" @click="sortBy('win_rate')">胜率 {{ sortIcon('win_rate') }}</text>
							<text class="opt-th opt-th-narrow" @click="sortBy('total_trades')">交易 {{ sortIcon('total_trades') }}</text>
							<text v-if="optHasOos" class="opt-th" @click="sortBy('oos_sharpe')">OOS {{ sortIcon('oos_sharpe') }}</text>
						</view>
						<view
							v-for="(row, idx) in sortedOptResults"
							:key="row.lookback_n + '_' + row.rebalance_days"
							:class="['opt-table-row', selectedRowKey === (row.lookback_n + '_' + row.rebalance_days) ? 'opt-row-selected' : '']"
							@click="selectRow(row)"
						>
							<text class="opt-td opt-td-narrow">{{ row.lookback_n }}</text>
							<text class="opt-td opt-td-narrow">{{ row.rebalance_days }}</text>
							<text class="opt-td" :class="profitClass(row.total_return)">{{ pct(row.total_return) }}</text>
							<text class="opt-td">{{ fmt(row.sharpe_ratio) }}<text v-if="row.robust === false" class="td-warn"> ⚠</text></text>
							<text class="opt-td">{{ fmt(row.smoothed_sharpe) }}</text>
							<text class="opt-td profit-down">{{ pctAbs(row.max_drawdown) }}</text>
							<text class="opt-td">{{ fmt(row.calmar_ratio) }}</text>
							<text class="opt-td">{{ pct(row.win_rate) }}</text>
							<text class="opt-td opt-td-narrow">{{ row.total_trades }}</text>
							<text v-if="optHasOos" class="opt-td">{{ fmt(row.oos_sharpe) }}</text>
						</view>
					</view>
					<!-- 选中行详情：净值曲线（IS / OOS 双色） -->
					<view v-if="selectedRow" class="opt-detail">
						<view class="opt-detail-head">
							<text class="opt-detail-title">选中参数：n={{ selectedRow.lookback_n }}, r={{ selectedRow.rebalance_days }}</text>
							<button class="apply-mini" type="warn" size="mini" @click="applyRow(selectedRow)">应用此参数</button>
						</view>
						<view id="opt-detail-chart" class="chart-container chart-container-sm"></view>
						<view v-if="optHasOos && selectedRow.oos_sharpe !== null" class="opt-detail-stats">
							<text class="opt-stat">样本内 Sharpe: <text class="opt-stat-val">{{ fmt(selectedRow.sharpe_ratio) }}</text></text>
							<text class="opt-stat">样本外 Sharpe: <text class="opt-stat-val">{{ fmt(selectedRow.oos_sharpe) }}</text></text>
							<text class="opt-stat">IS/OOS 衰减: <text class="opt-stat-val">{{ oosDecayPct(selectedRow) }}</text></text>
						</view>
					</view>
				</view>
				</view><!-- v-show optSectionOpen 结束 -->
			</view>
		</view>

		<!-- 回测结果区 -->
		<view v-if="hasResult" class="result-section">
			<view class="bt-section-box">
			<view class="section-title-row" @click="btSectionOpen = !btSectionOpen">
				<text class="section-title">回测结果</text>
				<text class="fold-icon">{{ btSectionOpen ? '▼' : '▶' }}</text>
			</view>
			<view v-show="btSectionOpen">
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
					<text class="summary-label">Calmar</text>
					<text class="summary-value">{{ summary.calmar_ratio || '-' }}</text>
				</view>
				<view class="summary-item">
					<text class="summary-label">胜率</text>
					<text class="summary-value">{{ ((summary.win_rate || 0) * 100).toFixed(1) }}%</text>
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
			</view><!-- v-show btSectionOpen 结束 -->
			</view><!-- bt-section-box 结束 -->
		</view>

		<!-- 底部订阅操作栏 -->
		<view class="goods-carts goods-carts2">
			<uni-goods-nav :options="navOptions" :buttonGroup="subBtnGroup" @buttonClick="onSubBtnClick" />
		</view>
	</view>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import getMomentumBacktest from '@/services/strategy/momentumBacktest.js'
import getMomentumOptimize from '@/services/strategy/momentumOptimize.js'
import etfNameLookup from '@/services/strategy/etfNameLookup.js'
import { getMy } from '@/services/sk/getMy.js'
import {
	getSubscription,
	createSubscription,
	updateSubscription,
} from '@/services/strategy/momentumSubscription.js'
import userStore from '@/stores/user.js'
import { handleVipBlocked } from '@/utils/vipTip.js'
import uniGoodsNav from '@dcloudio/uni-ui/lib/uni-goods-nav/uni-goods-nav.vue'

// 本地存储 key
const STORAGE_KEY = 'momentum_params'

// 参数
const etfList = ref([
	{ code: '518880', name: '' },
	{ code: '513100', name: '' },
	{ code: '510300', name: '' },
	{ code: '159915', name: '' },
])
const newEtfCode = ref('')
const nameLoading = ref(false)
const myWatchlist = ref([])  // [{code, name}] 关注列表，作为下拉候选
const startDate = ref('2024-01-01')
const endDate = ref(new Date().toISOString().slice(0, 10))
const lookbackN = ref(25)
const rebalanceDays = ref(5)
const initialCapital = ref(1000000)
const loading = ref(false)

// 保存参数到本地
const saveParams = () => {
	try {
		uni.setStorageSync(STORAGE_KEY, {
			etfList: etfList.value.map(e => ({ code: e.code, name: e.name })),
			startDate: startDate.value,
			endDate: endDate.value,
			lookbackN: lookbackN.value,
			rebalanceDays: rebalanceDays.value,
			initialCapital: initialCapital.value,
		})
	} catch (e) {
		console.error('保存参数失败', e)
	}
}

// 从本地恢复参数
const loadParams = () => {
	try {
		const saved = uni.getStorageSync(STORAGE_KEY)
		if (!saved) return false
		if (Array.isArray(saved.etfList) && saved.etfList.length >= 2) {
			etfList.value = saved.etfList.map(e => ({ code: e.code, name: e.name || '' }))
		}
		if (saved.startDate) startDate.value = saved.startDate
		if (saved.endDate) endDate.value = saved.endDate
		if (saved.lookbackN) lookbackN.value = saved.lookbackN
		if (saved.rebalanceDays) rebalanceDays.value = saved.rebalanceDays
		if (saved.initialCapital) initialCapital.value = saved.initialCapital
		return true
	} catch (e) {
		console.error('读取参数失败', e)
		return false
	}
}

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
const optBest = ref({})           // 兼容旧字段（夏普最高）
const optBestSharpe = ref(null)
const optBestRobust = ref(null)
const optBestOos = ref(null)
const optResults = ref([])
const optNList = ref([])
const optRList = ref([])
const optHasOos = ref(false)
const enableOos = ref(false)
const heatmapMetric = ref('composite')   // composite | sharpe | mdd | winrate | smoothed | oos
const sortKey = ref('sharpe_ratio')
const sortDir = ref('desc')           // 'asc' | 'desc'
const selectedRow = ref(null)
const btSectionOpen = ref(true)       // 回测结果折叠
const optSectionOpen = ref(true)      // 优化结果整体折叠
const optTableOpen = ref(false)       // 详细表格折叠（默认收起）

// 订阅状态
const subscribing = ref(false)
const editingSubId = ref(null)        // 修改模式下的订阅 id
const editingSubName = ref('')        // 修改模式下的订阅名称
const isEditMode = computed(() => editingSubId.value != null)

// 底部操作栏
const navOptions = ref([])
const subBtnGroup = computed(() => {
	if (isEditMode.value) {
		return [{ text: '保存修改', backgroundColor: '#ffa200', color: '#fff' }]
	}
	return [{ text: '订阅每日推送', backgroundColor: '#ffa200', color: '#fff' }]
})

// 图表实例
let momentumChart = null
let equityChart = null
let optimizeChart = null
let optDetailChart = null
let momentumTouchCleanup = null
let equityTouchCleanup = null
let optimizeTouchCleanup = null
let optDetailTouchCleanup = null

const selectedRowKey = computed(() =>
	selectedRow.value
		? selectedRow.value.lookback_n + '_' + selectedRow.value.rebalance_days
		: ''
)

// 排序后的结果
const sortedOptResults = computed(() => {
	const arr = [...optResults.value]
	const key = sortKey.value
	const dir = sortDir.value === 'asc' ? 1 : -1
	arr.sort((a, b) => {
		const va = a[key]
		const vb = b[key]
		if (va == null && vb == null) return 0
		if (va == null) return 1
		if (vb == null) return -1
		return va > vb ? dir : va < vb ? -dir : 0
	})
	return arr
})

const ETF_COLORS = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#fc8452']

// 手动 touch 捏合缩放 + 单指平移（参考股票详情页面）
function attachTouchZoom(dom, chart) {
	if (!dom || !chart) return () => {}

	let startDist = 0
	let startZoom = { start: 0, end: 100 }
	let lastSingleX = null
	let startSingleX = null
	let isDragging = false

	function getZoomState() {
		const opt = chart.getOption()
		const dz = opt.dataZoom && opt.dataZoom[0]
		if (!dz) return { start: 0, end: 100 }
		return { start: dz.start ?? 0, end: dz.end ?? 100 }
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
			const newRange = Math.min(100, Math.max(5, range * ratio))
			const mid = (startZoom.start + startZoom.end) / 2
			let ns = mid - newRange / 2
			let ne = mid + newRange / 2
			if (ns < 0) { ne -= ns; ns = 0 }
			if (ne > 100) { ns -= (ne - 100); ne = 100 }
			chart.dispatchAction({ type: 'dataZoom', dataZoomIndex: 0, start: Math.max(0, ns), end: Math.min(100, ne) })
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
			const shift = -(dx / (dom.offsetWidth || 1)) * range
			let ns = start + shift
			let ne = end + shift
			if (ns < 0) { ne -= ns; ns = 0 }
			if (ne > 100) { ns -= (ne - 100); ne = 100 }
			chart.dispatchAction({ type: 'dataZoom', dataZoomIndex: 0, start: Math.max(0, ns), end: Math.min(100, ne) })
		}
	}

	function onTouchEnd(e) {
		const wasTap = !isDragging && startSingleX !== null
		if (wasTap && e.changedTouches.length === 1) {
			const t = e.changedTouches[0]
			const rect = dom.getBoundingClientRect()
			chart.dispatchAction({
				type: 'showTip',
				x: t.clientX - rect.left,
				y: t.clientY - rect.top,
			})
		}
		startDist = 0
		lastSingleX = null
		startSingleX = null
		isDragging = false
	}

	dom.addEventListener('touchstart', onTouchStart, { passive: false })
	dom.addEventListener('touchmove', onTouchMove, { passive: false })
	dom.addEventListener('touchend', onTouchEnd)

	return () => {
		dom.removeEventListener('touchstart', onTouchStart)
		dom.removeEventListener('touchmove', onTouchMove)
		dom.removeEventListener('touchend', onTouchEnd)
	}
}

// uni-app: 接收页面跳转参数（?id=xxx 进入修改模式）
const pageQuery = ref({})
onLoad((options) => {
	pageQuery.value = options || {}
})

// 把订阅记录的参数填充到表单
function applySubscriptionToForm(sub) {
	if (!sub) return
	if (Array.isArray(sub.etf_codes) && sub.etf_codes.length) {
		etfList.value = sub.etf_codes.map(code => ({ code, name: '' }))
	}
	if (sub.lookback_n != null) lookbackN.value = sub.lookback_n
	if (sub.rebalance_days != null) rebalanceDays.value = sub.rebalance_days
	if (sub.initial_capital != null) initialCapital.value = sub.initial_capital
}

// 页面加载时先恢复本地参数，再补全ETF名称
onMounted(async () => {
	const subId = pageQuery.value.id
	// 修改模式：从后端拉订阅参数（不读本地）
	if (subId && userStore.isLoggedIn.value) {
		try {
			const res = await getSubscription(subId)
			if (res && res.code === 0 && res.data) {
				editingSubId.value = res.data.id
				editingSubName.value = res.data.name || '未命名订阅'
				applySubscriptionToForm(res.data)
			}
		} catch (e) {
			uni.showToast({ title: '加载订阅失败', icon: 'none' })
		}
	} else {
		loadParams()
	}
	// 仅对缺名称的标的请求一次
	const missingCodes = etfList.value.filter(e => !e.name).map(e => e.code)
	if (missingCodes.length > 0) {
		const names = await etfNameLookup(missingCodes.join(','))
		etfList.value.forEach(item => {
			if (!item.name && names[item.code]) item.name = names[item.code]
		})
	}
	// 加载关注列表作为下拉候选
	try {
		const res = await getMy()
		if (res && res.code === 0 && res.data && Array.isArray(res.data.userSkList)) {
			myWatchlist.value = res.data.userSkList.map(it => ({
				code: it.skId,
				name: it.skName,
			}))
		}
	} catch (e) {
		// 未登录或失败时静默
	}
})

const requireLogin = () => {
	if (userStore.isLoggedIn.value) return true
	uni.showModal({
		title: '需要登录',
		content: '订阅每日推送需要先登录，是否前往登录？',
		confirmText: '去登录',
		success: (r) => {
			if (r.confirm) {
				uni.navigateTo({ url: '/pages/auth/login' })
			}
		},
	})
	return false
}

function buildPayload() {
	return {
		etf_codes: etfList.value.map(e => e.code),
		lookback_n: Number(lookbackN.value),
		rebalance_days: Number(rebalanceDays.value),
		initial_capital: Number(initialCapital.value),
	}
}

// 创建：弹框输入名称 → POST
const doCreate = () => {
	if (!requireLogin()) return
	uni.showModal({
		title: '订阅命名',
		editable: true,
		placeholderText: '给这个订阅起个名字',
		success: async (r) => {
			if (!r.confirm) return
			const name = (r.content || '').trim() || '未命名订阅'
			subscribing.value = true
			try {
				const res = await createSubscription({ ...buildPayload(), name })
				if (handleVipBlocked(res)) return
				if (res && res.code === 0) {
					uni.showToast({ title: res.message || '订阅成功', icon: 'success' })
				} else {
					uni.showToast({ title: (res && res.message) || '订阅失败', icon: 'none' })
				}
			} catch (e) {
				uni.showToast({ title: '订阅请求失败', icon: 'none' })
			} finally {
				subscribing.value = false
			}
		},
	})
}

// 更新：直接 PUT
const doUpdate = async () => {
	if (!requireLogin()) return
	subscribing.value = true
	try {
		const res = await updateSubscription(editingSubId.value, buildPayload())
		if (handleVipBlocked(res)) return
		if (res && res.code === 0) {
			uni.showToast({ title: res.message || '已保存', icon: 'success' })
		} else {
			uni.showToast({ title: (res && res.message) || '保存失败', icon: 'none' })
		}
	} catch (e) {
		uni.showToast({ title: '保存失败', icon: 'none' })
	} finally {
		subscribing.value = false
	}
}

const onSubBtnClick = () => {
	if (subscribing.value) return
	if (isEditMode.value) doUpdate()
	else doCreate()
}

const removeEtf = (index) => {
	if (etfList.value.length <= 2) {
		uni.showToast({ title: '至少保留2个标的', icon: 'none' })
		return
	}
	etfList.value.splice(index, 1)
	saveParams()
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
		saveParams()
	} finally {
		nameLoading.value = false
	}
}

const onStartDateChange = (e) => {
	startDate.value = e.detail.value
	saveParams()
}

const onEndDateChange = (e) => {
	endDate.value = e.detail.value
	saveParams()
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
	if (!requireLogin()) return
	optimizing.value = true
	try {
		const formattedStart = startDate.value.replace(/-/g, '/')
		const formattedEnd = endDate.value.replace(/-/g, '/')

		const params = {
			codes: etfList.value.map(e => e.code).join(','),
			start_date: formattedStart,
			end_date: formattedEnd,
			initial_capital: initialCapital.value,
		}
		if (enableOos.value) {
			params.oos = 1
		}

		const res = await getMomentumOptimize(params)

		// VIP 配额拦截
		if (handleVipBlocked(res)) return

		if (res.code !== 0) {
			uni.showToast({ title: res.message || '优化失败', icon: 'none' })
			return
		}

		const data = res.data
		optResults.value = data.results || []
		optNList.value = data.n_list || []
		optRList.value = data.r_list || []
		optBest.value = data.best || {}
		optBestSharpe.value = data.best_sharpe || null
		optBestRobust.value = data.best_robust || null
		optBestOos.value = data.best_oos || null
		optHasOos.value = !!data.oos_enabled
		hasOptResult.value = true
		// 默认选中 sharpe 最高那行
		selectedRow.value = optBestSharpe.value

		await nextTick()
		const echarts = await loadEcharts()
		renderOptimizeChart(echarts)
		if (selectedRow.value) {
			renderOptDetailChart(echarts)
		}
	} catch (e) {
		console.error('优化失败', e)
		uni.showToast({ title: '参数优化请求失败', icon: 'none' })
	} finally {
		optimizing.value = false
	}
}

function getMetricVal(row, metric) {
	if (metric === 'sharpe') return row.sharpe_ratio
	if (metric === 'smoothed') return row.smoothed_sharpe
	if (metric === 'mdd') return row.max_drawdown
	if (metric === 'winrate') return row.win_rate
	if (metric === 'composite') return row.composite_score
	if (metric === 'oos') return row.oos_sharpe
	return row.sharpe_ratio
}

function metricLabel(metric) {
	return ({
		sharpe: 'Sharpe', smoothed: '平滑Sharpe', mdd: '最大回撤',
		winrate: '胜率', composite: '综合得分', oos: 'OOS Sharpe',
	})[metric] || metric
}

function renderOptimizeChart(echarts) {
	if (optimizeTouchCleanup) { optimizeTouchCleanup(); optimizeTouchCleanup = null }
	if (optimizeChart) { optimizeChart.dispose(); optimizeChart = null }
	const dom = document.getElementById('optimize-chart')
	if (!dom) return

	optimizeChart = echarts.init(dom)
	const results = optResults.value
	const nList = optNList.value
	const rList = optRList.value
	const metric = heatmapMetric.value

	const isMdd = metric === 'mdd'
	const isWinrate = metric === 'winrate'
	const heatData = []
	let minVal = Infinity, maxVal = -Infinity
	for (const row of results) {
		const ni = nList.indexOf(row.lookback_n)
		const ri = rList.indexOf(row.rebalance_days)
		let v = getMetricVal(row, metric)
		if (ni >= 0 && ri >= 0 && v != null) {
			if (isMdd) v = Math.abs(v)
			heatData.push([ni, ri, v])
			if (v < minVal) minVal = v
			if (v > maxVal) maxVal = v
		}
	}
	if (!isFinite(minVal)) { minVal = 0; maxVal = 1 }

	// 回撤：绝对值越小越好 → 绿；越大越差 → 红
	const colorRange = isMdd
		? ['#52c41a', '#eac736', '#d94e5d']
		: ['#d94e5d', '#eac736', '#50a3ba']

	optimizeChart.setOption({
		tooltip: {
			position: 'top',
			formatter: (p) => {
				const n = nList[p.value[0]]
				const r = rList[p.value[1]]
				const v = p.value[2]
				const row = results.find(x => x.lookback_n === n && x.rebalance_days === r)
				if (!row) return ''
				const lines = [
					`n=${n} / r=${r}`,
					`${metricLabel(metric)}: ${typeof v === 'number' ? v.toFixed(3) : v}`,
					`收益: ${(row.total_return * 100).toFixed(2)}%`,
					`回撤: ${(Math.abs(row.max_drawdown) * 100).toFixed(2)}%`,
				]
				if (row.robust === false) lines.push('⚠ 邻居波动大')
				return lines.join('<br/>')
			}
		},
		grid: { left: 40, right: 10, top: 10, bottom: 70 },
		xAxis: {
			type: 'category',
			data: nList.map(n => n + ''),
			name: '回看天数',
			nameLocation: 'center',
			nameGap: 25,
			splitArea: { show: true },
			axisLabel: { fontSize: 10 },
		},
		yAxis: {
			type: 'category',
			data: rList.map(r => r + ''),
			name: '调仓',
			splitArea: { show: true },
			axisLabel: { fontSize: 10 },
		},
		visualMap: {
			min: minVal,
			max: maxVal,
			calculable: true,
			orient: 'horizontal',
			left: 'center',
			bottom: 2,
			itemWidth: 12,
			itemHeight: 100,
			inRange: { color: colorRange },
			textStyle: { fontSize: 10 },
		},
		series: [{
			type: 'heatmap',
			data: heatData,
			label: {
				show: true,
				formatter: (p) => {
					const v = p.value[2]
					if (typeof v !== 'number') return ''
					if (isWinrate) return Math.round(v * 100) + '%'
					if (isMdd) return (v * 100).toFixed(0) + '%'
					return v.toFixed(2)
				},
				fontSize: 11,
			},
			emphasis: {
				itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' }
			},
		}],
	})
	optimizeTouchCleanup = attachTouchZoom(dom, optimizeChart)
}

async function switchHeatmap(metric) {
	heatmapMetric.value = metric
	await nextTick()
	const echarts = await loadEcharts()
	renderOptimizeChart(echarts)
}

function sortBy(key) {
	if (sortKey.value === key) {
		sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
	} else {
		sortKey.value = key
		sortDir.value = 'desc'
	}
}

function sortIcon(key) {
	if (sortKey.value !== key) return ''
	return sortDir.value === 'asc' ? '↑' : '↓'
}

async function selectRow(row) {
	selectedRow.value = row
	await nextTick()
	const echarts = await loadEcharts()
	renderOptDetailChart(echarts)
}

function selectByBest(which) {
	const row = which === 'sharpe' ? optBestSharpe.value
		: which === 'robust' ? optBestRobust.value
		: optBestOos.value
	if (row) selectRow(row)
}

function applyRow(row) {
	if (!row) return
	lookbackN.value = row.lookback_n
	rebalanceDays.value = row.rebalance_days
	saveParams()
	uni.showToast({ title: `已应用 n=${row.lookback_n}, r=${row.rebalance_days}`, icon: 'success' })
}

const applyBest = () => applyRow(optBest.value)

function renderOptDetailChart(echarts) {
	if (optDetailTouchCleanup) { optDetailTouchCleanup(); optDetailTouchCleanup = null }
	if (optDetailChart) { optDetailChart.dispose(); optDetailChart = null }
	const dom = document.getElementById('opt-detail-chart')
	if (!dom || !selectedRow.value) return

	optDetailChart = echarts.init(dom)
	const row = selectedRow.value
	const isCurve = row.is_equity_curve || []
	const oosCurve = row.oos_equity_curve || []

	const series = []
	if (isCurve.length) {
		series.push({
			name: '样本内',
			type: 'line',
			data: isCurve.map(it => [it[0], it[1]]),
			showSymbol: false,
			smooth: true,
			lineStyle: { width: 2, color: '#5470c6' },
			itemStyle: { color: '#5470c6' },
			areaStyle: { opacity: 0.1 },
		})
	}
	if (oosCurve.length) {
		series.push({
			name: '样本外',
			type: 'line',
			data: oosCurve.map(it => [it[0], it[1]]),
			showSymbol: false,
			smooth: true,
			lineStyle: { width: 2, color: '#ee6666' },
			itemStyle: { color: '#ee6666' },
			areaStyle: { opacity: 0.1 },
		})
	}

	optDetailChart.setOption({
		tooltip: {
			trigger: 'axis',
			formatter: (params) => {
				const lines = []
				params.forEach(p => {
					lines.push(`${p.seriesName}: ${(p.value[1] / 10000).toFixed(2)}万`)
				})
				return `${params[0].axisValue}<br/>${lines.join('<br/>')}`
			}
		},
		legend: { data: series.map(s => s.name), top: 0 },
		grid: { left: '12%', right: '4%', top: 30, bottom: 40 },
		xAxis: { type: 'time' },
		yAxis: {
			type: 'value',
			scale: true,
			axisLabel: { formatter: (v) => (v / 10000).toFixed(0) + '万' }
		},
		series,
	})
	optDetailTouchCleanup = attachTouchZoom(dom, optDetailChart)
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

function oosDecayPct(row) {
	if (!row || row.sharpe_ratio == null || row.oos_sharpe == null) return '-'
	if (row.sharpe_ratio === 0) return '-'
	const decay = (row.sharpe_ratio - row.oos_sharpe) / Math.abs(row.sharpe_ratio)
	return (decay * 100).toFixed(0) + '%'
}

function oosDecayLabel(row) {
	if (!row || row.oos_sharpe == null || row.sharpe_ratio == null) return ''
	const decay = (row.sharpe_ratio - row.oos_sharpe) / Math.max(Math.abs(row.sharpe_ratio), 0.01)
	if (decay <= 0.5) return '✓ OOS 与 IS 接近'
	return '⚠ OOS 衰减明显'
}

function onOosChange(e) {
	enableOos.value = e.detail.value
}

async function runBacktest() {
	if (!requireLogin()) return
	loading.value = true
	saveParams()
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

		// VIP 配额拦截
		if (handleVipBlocked(res)) return

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
	if (momentumTouchCleanup) { momentumTouchCleanup(); momentumTouchCleanup = null }
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
		       tooltip: {
			       trigger: 'axis',
			       position: function (point, params, dom, rect, size) {
				       // 左侧，顶部对齐
				       return [0, 0];
			       }
		       },
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
	momentumTouchCleanup = attachTouchZoom(dom, momentumChart)
}

function renderEquityChart(echarts, equityCurve) {
	if (equityTouchCleanup) { equityTouchCleanup(); equityTouchCleanup = null }
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
	equityTouchCleanup = attachTouchZoom(dom, equityChart)
}

// 窗口resize
function onResize() {
	momentumChart && momentumChart.resize()
	equityChart && equityChart.resize()
	optimizeChart && optimizeChart.resize()
	optDetailChart && optDetailChart.resize()
}

if (typeof window !== 'undefined') {
	window.addEventListener('resize', onResize)
}

onBeforeUnmount(() => {
	if (typeof window !== 'undefined') {
		window.removeEventListener('resize', onResize)
	}
	if (momentumTouchCleanup) { momentumTouchCleanup(); momentumTouchCleanup = null }
	if (equityTouchCleanup) { equityTouchCleanup(); equityTouchCleanup = null }
	if (optimizeTouchCleanup) { optimizeTouchCleanup(); optimizeTouchCleanup = null }
	if (optDetailTouchCleanup) { optDetailTouchCleanup(); optDetailTouchCleanup = null }
	if (momentumChart) { momentumChart.dispose(); momentumChart = null }
	if (equityChart) { equityChart.dispose(); equityChart = null }
	if (optimizeChart) { optimizeChart.dispose(); optimizeChart = null }
	if (optDetailChart) { optDetailChart.dispose(); optDetailChart = null }
})
</script>

<style>
.uni-container {
	padding: 12px;
	padding-bottom: 70px;
}

.edit-banner {
	background: #fff;
	border-radius: 8px;
	padding: 16px;
	margin-bottom: 12px;
	box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
	display: flex;
	align-items: center;
}

.edit-banner-label {
	font-size: 14px;
	color: #666;
	width: 80px;
	flex-shrink: 0;
}

.edit-banner-name {
	font-size: 16px;
	font-weight: 600;
	color: #333;
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

.goods-carts {
	display: flex;
	flex-direction: column;
	position: fixed;
	left: 0;
	right: 0;
	/* #ifdef H5 */
	left: var(--window-left);
	right: var(--window-right);
	/* #endif */
	bottom: 0;
	z-index: 99;
}

.goods-carts2 ::v-deep .uni-tab__cart-sub-left {
	display: none;
}

.goods-carts2 ::v-deep .uni-tab__cart-sub-right {
	flex: 1;
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

.summary-card {
	display: flex;
	flex-wrap: wrap;
	background: #fff;
	border-radius: 8px;
	padding: 8px 10px;
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
	padding: 10px;
	margin-bottom: 8px;
	box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.chart-container {
	width: 100%;
	height: 300px;
	touch-action: none;
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

/* ===== 折叠 ===== */
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

.sub-fold {
	margin-top: 12px;
	margin-bottom: 4px;
	padding: 8px 0;
	border-top: 1px dashed #ececec;
}

.sub-fold-label {
	font-size: 13px;
	color: #666;
	font-weight: 500;
}

/* ===== 优化结果新版样式 ===== */
.opt-extra-row {
	display: flex;
	align-items: center;
	gap: 8px;
}

.opt-extra-hint {
	font-size: 11px;
	color: #999;
}

.best-cards {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	margin-bottom: 12px;
}

.best-card {
	flex: 1;
	min-width: 200px;
	background: #fafbfc;
	border: 1px solid #e8eaed;
	border-radius: 8px;
	padding: 8px 10px;
	display: flex;
	flex-direction: column;
	gap: 4px;
	cursor: pointer;
	transition: box-shadow 0.15s;
}

.best-card:hover {
	box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.best-card-sharpe { border-left: 3px solid #faad14; }
.best-card-robust { border-left: 3px solid #52c41a; }
.best-card-oos { border-left: 3px solid #1890ff; }

.best-card-head {
	display: flex;
	justify-content: space-between;
	align-items: center;
}

.best-card-title {
	font-size: 13px;
	font-weight: 600;
	color: #333;
}

.best-warn {
	font-size: 11px;
	color: #d4380d;
	background: #fff1f0;
	border-radius: 10px;
	padding: 1px 6px;
}

.best-ok {
	font-size: 11px;
	color: #389e0d;
	background: #f6ffed;
	border-radius: 10px;
	padding: 1px 6px;
}

.best-card-param {
	font-size: 13px;
	font-weight: 600;
	color: #5470c6;
}

.best-card-metrics {
	display: flex;
	gap: 8px;
	flex-wrap: wrap;
}

.best-metric {
	display: flex;
	flex-direction: column;
	flex: 1;
	min-width: 60px;
}

.m-label {
	font-size: 10px;
	color: #999;
}

.m-val {
	font-size: 13px;
	font-weight: 600;
	color: #333;
}

.apply-mini {
	align-self: flex-start;
	font-size: 11px !important;
	min-height: 24px !important;
	line-height: 22px !important;
	padding: 0 10px !important;
	margin-top: 2px;
}

.heatmap-tabs {
	display: flex;
	gap: 6px;
	margin: 12px 0 4px;
	flex-wrap: wrap;
}

.heatmap-tab {
	font-size: 12px;
	color: #666;
	padding: 4px 10px;
	background: #f3f4f6;
	border-radius: 12px;
	cursor: pointer;
}

.heatmap-tab.active {
	background: #5470c6;
	color: #fff;
}

.opt-table-wrap {
	margin-top: 12px;
	border: 1px solid #ececec;
	border-radius: 6px;
	overflow-x: auto;
}

.opt-table-head {
	display: flex;
	background: #f7f8fa;
	border-bottom: 1px solid #ececec;
	min-width: 720px;
}

.opt-th {
	flex: 1;
	font-size: 11px;
	color: #666;
	padding: 8px 4px;
	text-align: center;
	cursor: pointer;
	user-select: none;
}

.opt-th-narrow {
	max-width: 50px;
}

.opt-table-row {
	display: flex;
	border-bottom: 1px solid #f3f3f3;
	min-width: 720px;
	cursor: pointer;
}

.opt-table-row:hover {
	background: #f9fbff;
}

.opt-row-selected {
	background: #fffbe6 !important;
}

.opt-td {
	flex: 1;
	font-size: 12px;
	color: #333;
	padding: 8px 4px;
	text-align: center;
}

.opt-td-narrow {
	max-width: 50px;
}

.td-warn {
	color: #d4380d;
	font-size: 11px;
}

.opt-detail {
	margin-top: 16px;
	padding-top: 12px;
	border-top: 1px dashed #ececec;
}

.opt-detail-head {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 8px;
}

.opt-detail-title {
	font-size: 13px;
	font-weight: 600;
	color: #333;
}

.chart-container-sm {
	height: 220px;
}

.opt-detail-stats {
	display: flex;
	gap: 12px;
	margin-top: 8px;
	flex-wrap: wrap;
}

.opt-stat {
	font-size: 12px;
	color: #666;
}

.opt-stat-val {
	color: #5470c6;
	font-weight: 600;
}
</style>

<template>
	<view class="uni-container">
		<view v-if="loading" class="loading-tip">加载中...</view>

		<view v-else-if="subscriptions.length === 0" class="empty-tip">
			<text class="empty-text">暂无订阅</text>
			<text class="empty-sub">前往策略页面订阅每日信号推送</text>
		</view>

		<view v-else class="sub-list">
			<view v-for="(item, index) in subscriptions" :key="item.strategy" class="sub-card">
				<view class="sub-header">
					<text class="sub-name">{{ item.strategy_name }}</text>
					<text :class="['sub-status', item.enabled ? 'status-on' : 'status-off']">
						{{ item.enabled ? '推送中' : '已暂停' }}
					</text>
				</view>

				<!-- 参数详情 -->
				<view class="sub-params">
					<view class="param-item">
						<text class="param-key">标的池</text>
						<text class="param-val">{{ (item.params.etf_codes || []).join(', ') }}</text>
					</view>

					<!-- 动量轮动特有参数 -->
					<template v-if="item.strategy === 'momentum'">
						<view class="param-item">
							<text class="param-key">回看天数</text>
							<text class="param-val">{{ item.params.lookback_n }} 天</text>
						</view>
						<view class="param-item">
							<text class="param-key">调仓周期</text>
							<text class="param-val">{{ item.params.rebalance_days }} 天</text>
						</view>
					</template>

					<!-- 均值回归特有参数 -->
					<template v-if="item.strategy === 'meanrev'">
						<view class="param-item">
							<text class="param-key">信号类型</text>
							<text class="param-val">{{ item.params.signal_type_label }}</text>
						</view>
						<view class="param-item">
							<text class="param-key">指标周期</text>
							<text class="param-val">{{ item.params.period }} 天</text>
						</view>
						<view class="param-item">
							<text class="param-key">调仓周期</text>
							<text class="param-val">{{ item.params.rebalance_days }} 天</text>
						</view>
						<view v-if="item.params.signal_type === 'bollinger'" class="param-item">
							<text class="param-key">标准差倍数</text>
							<text class="param-val">{{ item.params.num_std }}</text>
						</view>
						<view v-if="item.params.signal_type === 'rsi'" class="param-item">
							<text class="param-key">超卖阈值</text>
							<text class="param-val">{{ item.params.oversold }}</text>
						</view>
						<view class="param-item">
							<text class="param-key">止损</text>
							<text class="param-val">{{ (item.params.stop_loss * 100).toFixed(0) }}%</text>
						</view>
					</template>

					<view class="param-item">
						<text class="param-key">初始资金</text>
						<text class="param-val">{{ formatMoney(item.params.initial_capital) }}</text>
					</view>
				</view>

				<view class="sub-footer">
					<text class="sub-time">订阅时间：{{ formatDate(item.created_at) }}</text>
					<text class="sub-time">更新时间：{{ formatDate(item.updated_at) }}</text>
				</view>

				<view class="sub-actions">
					<button class="action-btn action-edit" type="default" size="mini"
						@click="goEditStrategy(item)">修改参数</button>
					<button class="action-btn action-cancel" type="default" size="mini"
						@click="cancelSubscription(item)">取消订阅</button>
				</view>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import getSubscriptions from '@/services/user/getSubscriptions.js'
import { deleteSubscription as deleteMomentum } from '@/services/strategy/momentumSubscription.js'
import { deleteSubscription as deleteMeanrev } from '@/services/strategy/meanrevSubscription.js'

const loading = ref(false)
const subscriptions = ref([])

const loadSubscriptions = async () => {
	loading.value = true
	try {
		const res = await getSubscriptions()
		if (res && res.code === 0 && res.data) {
			subscriptions.value = res.data.subscriptions || []
		}
	} catch (e) {
		console.error('加载订阅失败', e)
	} finally {
		loading.value = false
	}
}

onShow(async () => {
	await loadSubscriptions()
})

const formatMoney = (val) => {
	if (!val) return '0'
	return Number(val).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

const formatDate = (isoStr) => {
	if (!isoStr) return '-'
	return isoStr.slice(0, 16).replace('T', ' ')
}

const goEditStrategy = (item) => {
	if (item.strategy === 'momentum') {
		uni.navigateTo({ url: '/pages/strategy/momentum' })
	} else if (item.strategy === 'meanrev') {
		uni.navigateTo({ url: '/pages/strategy/meanrev' })
	}
}

const cancelSubscription = (item) => {
	const name = item.strategy_name
	uni.showModal({
		title: '取消订阅',
		content: `确定取消「${name}」的每日信号推送？`,
		success: async (r) => {
			if (!r.confirm) return
			try {
				let res
				if (item.strategy === 'momentum') {
					res = await deleteMomentum()
				} else if (item.strategy === 'meanrev') {
					res = await deleteMeanrev()
				}
				if (res && res.code === 0) {
					uni.showToast({ title: '已取消订阅', icon: 'success' })
					await loadSubscriptions()
				} else {
					uni.showToast({ title: '取消失败', icon: 'none' })
				}
			} catch (e) {
				uni.showToast({ title: '取消失败', icon: 'none' })
			}
		},
	})
}
</script>

<style>
.uni-container {
	padding: 12px;
}

.loading-tip {
	text-align: center;
	padding: 60px 0;
	color: #999;
	font-size: 14px;
}

.empty-tip {
	text-align: center;
	padding: 80px 0;
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 8px;
}

.empty-text {
	font-size: 16px;
	color: #666;
}

.empty-sub {
	font-size: 13px;
	color: #aaa;
}

.sub-list {
	display: flex;
	flex-direction: column;
	gap: 14px;
}

.sub-card {
	background: #fff;
	border-radius: 10px;
	padding: 16px;
	box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.sub-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 12px;
}

.sub-name {
	font-size: 16px;
	font-weight: 600;
	color: #333;
}

.sub-status {
	font-size: 12px;
	padding: 2px 10px;
	border-radius: 10px;
}

.status-on {
	background: #e8f5e9;
	color: #2e7d32;
}

.status-off {
	background: #f5f5f5;
	color: #999;
}

.sub-params {
	display: flex;
	flex-direction: column;
	gap: 6px;
	padding: 10px 0;
	border-top: 1px solid #f0f0f0;
	border-bottom: 1px solid #f0f0f0;
}

.param-item {
	display: flex;
	justify-content: space-between;
	font-size: 13px;
}

.param-key {
	color: #888;
}

.param-val {
	color: #333;
	font-weight: 500;
}

.sub-footer {
	padding: 8px 0;
	display: flex;
	flex-direction: column;
	gap: 2px;
}

.sub-time {
	font-size: 12px;
	color: #bbb;
}

.sub-actions {
	display: flex;
	gap: 10px;
	margin-top: 8px;
}

.action-btn {
	flex: 1;
	font-size: 13px;
	border-radius: 6px;
}

.action-edit {
	background: #5470c6;
	color: #fff;
}

.action-cancel {
	background: #f5f5f5;
	color: #999;
}
</style>

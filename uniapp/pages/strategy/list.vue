<template>
	<view class="uni-container">
		<view class="strategy-header">
			<text class="header-title">回测策略</text>
		</view>
		<view class="strategy-list">
			<view class="strategy-card" v-for="(item, index) in strategies" :key="index" @click="goToStrategy(item)">
				<view :class="['card-icon-wrap', item.iconBg]">
					<text class="card-icon">{{ item.icon }}</text>
				</view>
				<view class="card-content">
					<text class="card-title">{{ item.name }}</text>
					<text class="card-desc">{{ item.description }}</text>
				</view>
				<text class="card-arrow">></text>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref } from 'vue'

const strategies = ref([
	{
		id: 'momentum_rotation',
		name: '动量轮动策略',
		description: '基于动量评分在多个ETF间轮动，自动选择趋势最强的标的持仓',
		page: '/pages/strategy/momentum',
		icon: '\u26A1',
		iconBg: 'icon-bg-blue',
	},
	{
		id: 'mean_reversion',
		name: '均值回归策略',
		description: '基于布林带/RSI信号，在ETF超卖时买入、回归均值时卖出',
		page: '/pages/strategy/meanrev',
		icon: '\u21C4',
		iconBg: 'icon-bg-purple',
	},
	{
		id: 'combo',
		name: '策略组合回测',
		description: '将动量轮动与均值回归组合，按比例分配资金，对比单策略与组合的表现',
		page: '/pages/strategy/combo',
		icon: '\u2696',
		iconBg: 'icon-bg-orange',
	}
])

const goToStrategy = (item) => {
	uni.navigateTo({
		url: item.page,
		animationType: 'slide-in-right',
		animationDuration: 200
	})
}
</script>

<style>
.uni-container {
	padding: 12px;
}

.strategy-header {
	padding: 16px 4px 12px;
}

.header-title {
	font-size: 20px;
	font-weight: bold;
	color: #333;
}

.strategy-list {
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.strategy-card {
	display: flex;
	flex-direction: row;
	align-items: center;
	padding: 16px;
	background-color: #fff;
	border-radius: 10px;
	box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.card-icon-wrap {
	width: 44px;
	height: 44px;
	border-radius: 10px;
	display: flex;
	align-items: center;
	justify-content: center;
	margin-right: 14px;
	flex-shrink: 0;
}

.card-icon {
	font-size: 22px;
}

.icon-bg-blue {
	background: #e3f2fd;
}
.icon-bg-blue .card-icon {
	color: #1976d2;
}

.icon-bg-purple {
	background: #f3e5f5;
}
.icon-bg-purple .card-icon {
	color: #8e24aa;
}

.icon-bg-orange {
	background: #fff3e0;
}
.icon-bg-orange .card-icon {
	color: #ef6c00;
}

.card-content {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.card-title {
	font-size: 16px;
	font-weight: 600;
	color: #333;
}

.card-desc {
	font-size: 13px;
	color: #888;
	line-height: 1.4;
}

.card-arrow {
	font-size: 18px;
	color: #ccc;
	padding-left: 8px;
}
</style>

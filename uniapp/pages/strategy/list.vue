<template>
	<view class="uni-container">
		<view class="strategy-header">
			<text class="header-title">回测策略</text>
		</view>
		<view class="strategy-list">
			<view class="strategy-card" v-for="(item, index) in strategies" :key="index" @click="goToStrategy(item)">
				<view class="card-left">
					<text class="card-title">{{ item.name }}</text>
					<text class="card-desc">{{ item.description }}</text>
				</view>
				<view class="card-right">
					<text class="card-arrow">></text>
				</view>
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
		page: '/pages/strategy/momentum'
	},
	{
		id: 'mean_reversion',
		name: '均值回归策略',
		description: '基于布林带/RSI信号，在ETF超卖时买入、回归均值时卖出，高抛低吸',
		page: '/pages/strategy/meanrev'
	},
	{
		id: 'combo',
		name: '策略组合回测',
		description: '将动量轮动与均值回归组合，按比例分配资金，对比单策略与组合的表现',
		page: '/pages/strategy/combo'
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
	justify-content: space-between;
	padding: 16px;
	background-color: #fff;
	border-radius: 8px;
	box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.card-left {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: 6px;
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

.card-right {
	padding-left: 12px;
}

.card-arrow {
	font-size: 18px;
	color: #ccc;
}
</style>

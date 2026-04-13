<template>
	<view class="my-page">
		<!-- 顶部用户信息条 -->
		<view class="user-bar">
			<uni-row class="user-row">
				<uni-col :span="8" class="user-col">
					<img
						:src="userInfo.userImage || defaultAvatar"
						class="user-image"
					/>
				</uni-col>
				<uni-col :span="16" class="user-info">
					<!-- 已登录 -->
					<template v-if="isLoggedIn">
						<view>{{ userInfo.userName }}</view>
						<view>等級：{{ userInfo.userLevel || '普通' }}</view>
						<view v-if="userInfo.is_vip">VIP 用户</view>
						<view v-else>免费回测：{{ userInfo.backtest_count || 0 }} / {{ userInfo.backtest_quota || 20 }}</view>
					</template>
					<!-- 未登录 -->
					<template v-else>
						<view class="not-login-tip">未登录</view>
						<view class="user-actions">
							<text class="user-action-btn" @click="goLogin">登录</text>
							<text class="user-action-btn" @click="goRegister">注册</text>
						</view>
					</template>
				</uni-col>
			</uni-row>
		</view>

		<!-- 功能入口（仅登录后展示） -->
		<view v-if="isLoggedIn" class="menu-section">
			<view class="menu-card" @click="goWatchlist">
				<view class="menu-icon-wrap icon-bg-amber">
					<text class="menu-icon">&#9733;</text>
				</view>
				<view class="menu-content">
					<text class="menu-title">我的关注</text>
					<text class="menu-desc">查看自选股列表，点击可查看股票详情</text>
				</view>
				<text class="menu-arrow">></text>
			</view>
			<view class="menu-card" @click="goSubscriptions">
				<view class="menu-icon-wrap icon-bg-green">
					<text class="menu-icon">&#9993;</text>
				</view>
				<view class="menu-content">
					<text class="menu-title">我的订阅</text>
					<text class="menu-desc">查看已订阅的策略推送，管理订阅参数</text>
				</view>
				<text class="menu-arrow">></text>
			</view>
			<view class="menu-card menu-card-logout" @click="onLogout">
				<view class="menu-icon-wrap icon-bg-grey">
					<text class="menu-icon">&#10140;</text>
				</view>
				<view class="menu-content">
					<text class="menu-title menu-title-muted">退出登录</text>
					<text class="menu-desc">退出当前账号</text>
				</view>
				<text class="menu-arrow">></text>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import userStore from '@/stores/user.js'
import uniRow from '@dcloudio/uni-ui/lib/uni-row/uni-row.vue'
import uniCol from '@dcloudio/uni-ui/lib/uni-col/uni-col.vue'

const defaultAvatar = 'https://vkceyugu.cdn.bspapp.com/VKCEYUGU-dc-site/094a9dc0-50c0-11eb-b680-7980c8a877b8.jpg'

const isLoggedIn = computed(() => userStore.isLoggedIn.value)

const userInfo = ref({
	userName: '',
	userImage: '',
	userLevel: '',
	userLevelTimeLimit: '',
	is_vip: false,
	backtest_count: 0,
	backtest_quota: 20,
})

onShow(async () => {
	const u = userStore.state.user
	if (u) {
		userInfo.value = {
			...userInfo.value,
			userName: u.nickname || u.username,
			is_vip: u.is_vip,
			backtest_count: u.backtest_count,
			backtest_quota: u.backtest_quota,
		}
	} else {
		userInfo.value = {
			userName: '',
			userImage: '',
			userLevel: '',
			userLevelTimeLimit: '',
			is_vip: false,
			backtest_count: 0,
			backtest_quota: 20,
		}
	}
})

const goWatchlist = () => {
	uni.navigateTo({
		url: '/pages/skmy/watchlist',
		animationType: 'slide-in-right',
		animationDuration: 200,
	})
}

const goSubscriptions = () => {
	uni.navigateTo({
		url: '/pages/skmy/subscriptions',
		animationType: 'slide-in-right',
		animationDuration: 200,
	})
}

const goLogin = () => uni.navigateTo({ url: '/pages/auth/login' })
const goRegister = () => uni.navigateTo({ url: '/pages/auth/register' })

const onLogout = () => {
	uni.showModal({
		title: '退出登录',
		content: '确定要退出当前账号吗？',
		success: (r) => {
			if (!r.confirm) return
			userStore.logout()
			userInfo.value = {
				userName: '',
				userImage: '',
				userLevel: '',
				userLevelTimeLimit: '',
				is_vip: false,
				backtest_count: 0,
				backtest_quota: 20,
			}
		},
	})
}
</script>

<style>
.user-bar {
	padding: 16px 10px;
	background-color: #94bcff;
}
.user-bar .uni-row {
	width: 100%;
	display: flex;
	align-items: center;
}
.user-col {
	height: 100%;
	display: flex;
	align-items: center;
	justify-content: center;
}
.user-info {
	display: flex;
	flex-direction: column;
	justify-content: center;
	align-items: flex-start;
	color: #ffffff;
	height: 100%;
	font-size: 16px;
	gap: 4px;
}
.user-image {
	height: 20vmin;
	width: 20vmin;
	border-radius: 50%;
	object-fit: cover;
}
.not-login-tip {
	font-size: 16px;
	margin-bottom: 6px;
}
.user-actions {
	display: flex;
	gap: 10px;
	margin-top: 6px;
}
.user-action-btn {
	display: inline-block;
	padding: 4px 14px;
	background: #fff;
	color: #94bcff;
	border-radius: 14px;
	font-size: 13px;
	font-weight: 500;
}

.menu-section {
	padding: 16px 12px;
	display: flex;
	flex-direction: column;
	gap: 12px;
}

.menu-card {
	display: flex;
	flex-direction: row;
	align-items: center;
	padding: 16px;
	background-color: #fff;
	border-radius: 10px;
	box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.menu-card-logout {
	margin-top: 12px;
}

.menu-icon-wrap {
	width: 44px;
	height: 44px;
	border-radius: 10px;
	display: flex;
	align-items: center;
	justify-content: center;
	margin-right: 14px;
	flex-shrink: 0;
}

.icon-bg-amber {
	background: #fff8e1;
}
.icon-bg-amber .menu-icon {
	color: #f5a623;
}

.icon-bg-green {
	background: #e8f5e9;
}
.icon-bg-green .menu-icon {
	color: #43a047;
}

.icon-bg-grey {
	background: #f5f5f5;
}
.icon-bg-grey .menu-icon {
	color: #999;
}

.menu-icon {
	font-size: 22px;
}

.menu-content {
	flex: 1;
	display: flex;
	flex-direction: column;
	gap: 4px;
}

.menu-title {
	font-size: 16px;
	font-weight: 600;
	color: #333;
}

.menu-title-muted {
	color: #999;
}

.menu-desc {
	font-size: 13px;
	color: #999;
	line-height: 1.4;
}

.menu-arrow {
	font-size: 18px;
	color: #ccc;
	padding-left: 8px;
}
</style>

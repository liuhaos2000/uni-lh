<template>
	<view class="uni-container">
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
						<view class="user-actions">
							<text class="user-action-btn logout-btn" @click="onLogout">退出登录</text>
						</view>
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

		<!-- 自选股表格（仅登录后展示） -->
		<view v-if="isLoggedIn" style="padding: 10px 0 10px 0;">
			<view class="uni-container">
				<uni-table ref="table" :loading="loading" border stripe emptyText="暂无更多数据">
					<uni-tr>
						<uni-th width="80" align="center">代碼</uni-th>
						<uni-th width="80" align="center">名稱</uni-th>
						<uni-th width="20" align="center">價格</uni-th>
						<uni-th width="20" align="center">漲跌</uni-th>
					</uni-tr>
					<uni-tr v-for="(item, index) in tableData" :key="index" @click="handleRowClick(item)"
						:class="{ 'positive-movement': item.movement > 0, 'negative-movement': item.movement < 0 }">
						<uni-td>{{ item.skId }}</uni-td>
						<uni-td>{{ item.skName }}</uni-td>
						<uni-td align="right">{{ item.price }}</uni-td>
						<uni-td align="right">{{ item.movement }}</uni-td>
					</uni-tr>
				</uni-table>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import getMy from '@/services/sk/getMy.js'
import userStore from '@/stores/user.js'
import uniTable from '@dcloudio/uni-ui/lib/uni-table/uni-table.vue'
import uniTr from '@dcloudio/uni-ui/lib/uni-tr/uni-tr.vue'
import uniTh from '@dcloudio/uni-ui/lib/uni-th/uni-th.vue'
import uniTd from '@dcloudio/uni-ui/lib/uni-td/uni-td.vue'
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

const loading = ref(false)
const tableData = ref([])

const loadTableData = async () => {
	if (!isLoggedIn.value) return
	try {
		loading.value = true
		const result = await getMy()
		if (result && result.code === 0 && result.data) {
			tableData.value = result.data.userSkList || []
			userInfo.value = { ...userInfo.value, ...result.data }
		}
	} catch (e) {
		console.error('表格数据加载失败', e)
	} finally {
		loading.value = false
	}
}

// tabBar 页面不会销毁，每次进入都用 onShow 刷新
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
		// 退出登录后清空
		userInfo.value = {
			userName: '',
			userImage: '',
			userLevel: '',
			userLevelTimeLimit: '',
			is_vip: false,
			backtest_count: 0,
			backtest_quota: 20,
		}
		tableData.value = []
	}
	await loadTableData()
})

const handleRowClick = (item) => {
	uni.navigateTo({
		url: `/pages/sk/sk?skId=${encodeURIComponent(item.skId)}&skName=${encodeURIComponent(item.skName)}`,
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
			tableData.value = []
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
	padding: 10px;
	background-color: #94bcff;
}
.user-row {
	min-height: 26vmin;
}
.user-col {
	height: 100%;
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
	display: flex;
	flex-direction: column;
	justify-content: center;
	align-items: flex-start;
	height: 20vmin;
	width: 20vmin;
	padding: 12px;
	border-radius: 50%;
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
.logout-btn {
	background: rgba(255, 255, 255, 0.2);
	color: #fff;
}

.positive-movement {
	color: #D90214;
}
.negative-movement {
	color: #54ac54;
}
.positive-movement td {
	color: inherit !important;
}
.negative-movement td {
	color: inherit !important;
}
</style>

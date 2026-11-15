<template>
	<view class="uni-container">
		<uniSearchBar :focus="true" v-model="searchValue" @cancel="clear" @clear="clear" />
		<view class="search-results">
			<uni-table :loading="loading" border stripe emptyText="暂无更多数据">
				<uni-tr>
					<uni-th width="96" align="center">代碼</uni-th>
					<uni-th align="left">名稱</uni-th>
					<uni-th width="112" align="center">关注</uni-th>
				</uni-tr>
				<uni-tr v-for="item in tableData" :key="item.dm" @click="handleRowClick(item)">
					<uni-td align="center">{{ item.dm }}</uni-td>
					<uni-td>{{ item.mc }}</uni-td>
					<uni-td class="follow-cell" align="center">
						<button class="follow-button" size="mini"
							:type="followedCodes.has(stockKey(item.dm)) ? 'default' : 'primary'"
							:loading="pendingCodes.has(stockKey(item.dm))"
							:disabled="loadingWatchlist || pendingCodes.has(stockKey(item.dm))"
							@click.stop="toggleFollow(item.dm)">
							{{ followedCodes.has(stockKey(item.dm)) ? '取消关注' : '关注' }}
						</button>
					</uni-td>
				</uni-tr>
			</uni-table>
		</view>
	</view>
</template>

<script setup>
	import { computed, onMounted, ref } from 'vue'
	import { onShow } from '@dcloudio/uni-app'
	import uniTable from '@dcloudio/uni-ui/lib/uni-table/uni-table.vue'
	import uniTr from '@dcloudio/uni-ui/lib/uni-tr/uni-tr.vue'
	import uniTh from '@dcloudio/uni-ui/lib/uni-th/uni-th.vue'
	import uniTd from '@dcloudio/uni-ui/lib/uni-td/uni-td.vue'
	import uniSearchBar from '@dcloudio/uni-ui/lib/uni-search-bar/uni-search-bar.vue'
	import getStrategy2 from '@/services/sk/getStrategy2.js'
	import { addToWatchlist, getWatchlistCodes, removeFromWatchlist } from '@/services/sk/watchlist.js'
	import { tokenStore } from '@/utils/request.js'

	const searchValue = ref('')
	const allnames = ref([])
	const loading = ref(false)
	const loadingWatchlist = ref(false)
	const watchlistLoaded = ref(false)
	const followedCodes = ref(new Map())
	const pendingCodes = ref(new Set())

	const tableData = computed(() => {
		const query = searchValue.value.trim().toLowerCase()
		if (!query) return []
		return allnames.value.filter(({ dm, mc }) =>
			dm?.toLowerCase().includes(query) || mc?.toLowerCase().includes(query)
		)
	})

	// Keep the same six-digit code used by the stock detail page.
	const stockKey = (code) => code.slice(0, 6)

	onMounted(async () => {
		loading.value = true
		try {
			const result = await getStrategy2()
			allnames.value = result?.allnames || []
		} catch (error) {
			console.error('股票列表加载失败', error)
		} finally {
			loading.value = false
		}
	})

	const loadWatchlist = async () => {
		if (loadingWatchlist.value) return false
		watchlistLoaded.value = false
		loadingWatchlist.value = true
		try {
			const result = await getWatchlistCodes()
			if (result?.code !== 0) throw new Error('关注列表加载失败')
			followedCodes.value = new Map(result.data.map(code => [stockKey(code), code]))
			watchlistLoaded.value = true
			return true
		} catch (error) {
			if (error?.code !== 401) {
				uni.showToast({ title: '关注列表加载失败', icon: 'none' })
			}
			return false
		} finally {
			loadingWatchlist.value = false
		}
	}

	onShow(async () => {
		if (tokenStore.getAccess()) {
			await loadWatchlist()
		} else {
			watchlistLoaded.value = false
			followedCodes.value.clear()
		}
	})

	const toggleFollow = async (stockCode) => {
		if (!tokenStore.getAccess()) {
			uni.navigateTo({ url: '/pages/auth/login' })
			return
		}
		const key = stockKey(stockCode)
		if (loadingWatchlist.value || pendingCodes.value.has(key)) return
		if (!watchlistLoaded.value && !(await loadWatchlist())) return

		const storedCode = followedCodes.value.get(key)
		pendingCodes.value.add(key)
		try {
			const response = storedCode ? await removeFromWatchlist(storedCode) : await addToWatchlist(key)
			if (response?.code !== 0) throw new Error('关注操作失败')
			if (storedCode) {
				followedCodes.value.delete(key)
			} else {
				followedCodes.value.set(key, key)
			}
		} catch (error) {
			if (error?.code !== 401) {
				uni.showToast({ title: storedCode ? '取消关注失败' : '关注失败', icon: 'none' })
			}
		} finally {
			pendingCodes.value.delete(key)
		}
	}

	const clear = () => {
		searchValue.value = ''
	}

	const handleRowClick = ({ dm, mc }) => {
		uni.navigateTo({
			url: `/pages/sk/sk?skId=${encodeURIComponent(dm)}&skName=${encodeURIComponent(mc)}`,
			animationType: 'slide-in-right',
			animationDuration: 200,
		})
	}
</script>

<style scoped>
	.search-results {
		padding-bottom: 50px;
	}

	.search-results :deep(.uni-table) {
		table-layout: fixed;
	}

	.follow-cell,
	.follow-button {
		vertical-align: middle;
	}
</style>

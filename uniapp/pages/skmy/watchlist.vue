<template>
	<view class="uni-container">
		<view style="padding: 10px 0 10px 0;">
			<view class="uni-container watchlist-table">
				<uni-table :loading="loading" border stripe emptyText="暂无关注">
					<uni-tr>
						<uni-th width="96" align="center">代碼</uni-th>
						<uni-th align="left">名稱</uni-th>
						<uni-th width="112" align="center">关注</uni-th>
					</uni-tr>
					<uni-tr v-for="item in tableData" :key="item.skId" @click="handleRowClick(item)">
						<uni-td align="center">{{ item.skId }}</uni-td>
						<uni-td>{{ item.skName }}</uni-td>
						<uni-td class="follow-cell" align="center">
							<button class="follow-button" size="mini" type="default"
								:loading="pendingCodes.has(item.skId)"
								:disabled="loading || pendingCodes.has(item.skId)"
								@click.stop="unfollow(item.skId)">取消关注</button>
						</uni-td>
					</uni-tr>
				</uni-table>
			</view>
		</view>
	</view>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import getStrategy2 from '@/services/sk/getStrategy2.js'
import { getWatchlistCodes, removeFromWatchlist } from '@/services/sk/watchlist.js'
import uniTable from '@dcloudio/uni-ui/lib/uni-table/uni-table.vue'
import uniTr from '@dcloudio/uni-ui/lib/uni-tr/uni-tr.vue'
import uniTh from '@dcloudio/uni-ui/lib/uni-th/uni-th.vue'
import uniTd from '@dcloudio/uni-ui/lib/uni-td/uni-td.vue'

const loading = ref(false)
const stockCodes = ref([])
const stockNames = ref(new Map())
const pendingCodes = ref(new Set())

const tableData = computed(() => stockCodes.value.map(skId => ({
	skId,
	skName: stockNames.value.get(skId.slice(0, 6)) || skId,
})))

onMounted(async () => {
	try {
		const result = await getStrategy2()
		stockNames.value = new Map((result?.allnames || []).map(({ dm, mc }) => [dm.slice(0, 6), mc]))
	} catch (error) {
		console.error('股票名称加载失败', error)
	}
})

onShow(async () => {
	if (loading.value || pendingCodes.value.size) return
	loading.value = true
	try {
		const result = await getWatchlistCodes()
		if (result?.code !== 0) throw new Error('关注列表加载失败')
		stockCodes.value = [...new Set(result.data)]
	} catch (error) {
		if (error?.code !== 401) {
			uni.showToast({ title: '关注列表加载失败', icon: 'none' })
		}
	} finally {
		loading.value = false
	}
})

const unfollow = async (stockCode) => {
	if (loading.value || pendingCodes.value.has(stockCode)) return
	pendingCodes.value.add(stockCode)
	try {
		const result = await removeFromWatchlist(stockCode)
		if (result?.code !== 0 && result?.message !== 'stock_not_found' && result?.message !== 'watchlist_not_found') {
			throw new Error('取消关注失败')
		}
		stockCodes.value = stockCodes.value.filter(code => code !== stockCode)
		uni.showToast({ title: '已取消关注', icon: 'success' })
	} catch (error) {
		if (error?.code !== 401) {
			uni.showToast({ title: '取消关注失败', icon: 'none' })
		}
	} finally {
		pendingCodes.value.delete(stockCode)
	}
}

const handleRowClick = (item) => {
	uni.navigateTo({
		url: `/pages/sk/sk?skId=${encodeURIComponent(item.skId)}&skName=${encodeURIComponent(item.skName)}`,
		animationType: 'slide-in-right',
		animationDuration: 200,
	})
}
</script>

<style scoped>
.watchlist-table :deep(.uni-table) {
	table-layout: fixed;
}

.follow-cell,
.follow-button {
	vertical-align: middle;
}
</style>

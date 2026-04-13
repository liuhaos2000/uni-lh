<template>
	<view class="uni-container">
		<view style="padding: 10px 0 10px 0;">
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
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import getMy from '@/services/sk/getMy.js'
import uniTable from '@dcloudio/uni-ui/lib/uni-table/uni-table.vue'
import uniTr from '@dcloudio/uni-ui/lib/uni-tr/uni-tr.vue'
import uniTh from '@dcloudio/uni-ui/lib/uni-th/uni-th.vue'
import uniTd from '@dcloudio/uni-ui/lib/uni-td/uni-td.vue'

const loading = ref(false)
const tableData = ref([])

const loadTableData = async () => {
	try {
		loading.value = true
		const result = await getMy()
		if (result && result.code === 0 && result.data) {
			tableData.value = result.data.userSkList || []
		}
	} catch (e) {
		console.error('表格数据加载失败', e)
	} finally {
		loading.value = false
	}
}

onShow(async () => {
	await loadTableData()
})

const handleRowClick = (item) => {
	uni.navigateTo({
		url: `/pages/sk/sk?skId=${encodeURIComponent(item.skId)}&skName=${encodeURIComponent(item.skName)}`,
		animationType: 'slide-in-right',
		animationDuration: 200,
	})
}
</script>

<style>
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

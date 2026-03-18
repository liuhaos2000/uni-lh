<template>

	<view class="uni-container">
		<view style="padding: 10px; background-color: #94bcff;">
			<uni-row class="user-row">
				<uni-col :span="8" class="user-col">
					<img :src="userInfo.userImage" 
							class="user-image"></img>
				</uni-col>
				<uni-col :span="16" class="user-info">
					<view class="">{{ userInfo.userName }}</view>
					<view class="">等級：VIP⚜️</view>
					<view class="">期限：{{ userInfo.userLevelTimeLimit }}</view>
				</uni-col>
			</uni-row>
		</view>
		
		<view style="padding: 10px 0 10px 0;">
			<view class="uni-container">
				<uni-table ref="table" :loading="loading" border stripe emptyText="暂无更多数据"
					@selection-change="selectionChange">
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
	import { ref, onMounted } from 'vue'
	import getMy from '@/services/sk/getMy.js'
	import uniTable from '@dcloudio/uni-ui/lib/uni-table/uni-table.vue'
	import uniTr from '@dcloudio/uni-ui/lib/uni-tr/uni-tr.vue'
	import uniTh from '@dcloudio/uni-ui/lib/uni-th/uni-th.vue'
	import uniTd from '@dcloudio/uni-ui/lib/uni-td/uni-td.vue'
	import uniRow from '@dcloudio/uni-ui/lib/uni-row/uni-row.vue'
	import uniCol from '@dcloudio/uni-ui/lib/uni-col/uni-col.vue'


	// userInfo
	const userInfo = ref({
		userName:"",
		userImage:"",
		userLevel:"",
		userLevelTimeLimit:""
	})

	// 表格相关的响应式数据
	const loading = ref(false)
	const tableData = ref([])

	// 加载表格数据的方法
	const loadTableData = async () => {
		try {
			loading.value = true
			const result = await getMy()
			console.log('findsk:', result.data); // 调试输出
			tableData.value = result.data.userSkList
			userInfo.value= {...result.data};

		} catch (e) {
			console.error('表格数据加载失败', e)
		} finally {
			loading.value = false
		}
	}

	onMounted(async () => {
		// 1 加载表格数据
		await loadTableData()
	})

	// 处理表格行点击事件
	const handleRowClick = (item) => {
		// 使用 uni.navigateTo 进行页面跳转
		uni.navigateTo({
			url: `/pages/sk/sk?skId=${encodeURIComponent(item.skId)}&skName=${encodeURIComponent(item.skName)}`,
			animationType: 'slide-in-right',
			animationDuration: 200
		})
	}
</script>


<style>
	/* 涨幅大于0的行 */
	.positive-movement {
		color: #D90214; /* 浅红色背景 */
	}

	/* 涨幅小于0的行 */
	.negative-movement {
		color: #54ac54; /* 浅绿色背景 */
	}

	/* 确保 td 继承 tr 的字体颜色 */
	.positive-movement td {
		color: inherit !important; /* 继承父元素的颜色 */
	}
	.negative-movement td {
		color: inherit !important; /* 继承父元素的颜色 */
	}
	.user-row{
		height: 26vmin;
	}
	.user-col{
		height: 100%;
	}
	.user-info{
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: flex-start;
		color: #ffffff;
		height: 100%;
		font-size: 16px;
	}
	.user-image{
		display: flex;
		flex-direction: column; /* 垂直排列 */
		justify-content: center; /* 垂直居中 */
		align-items: flex-start; /* 水平靠左对齐 */
		height:20vmin; /* 确保容器高度为100% */
		width: 20vmin;
  		padding: 12px; /* 可选：添加内边距以便观察效果 */
		border-radius: 50%;
	}
</style>



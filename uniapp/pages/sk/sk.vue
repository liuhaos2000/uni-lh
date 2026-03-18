<template>
	<view class="uni-container">
		<view class="page">
			<div id="sk-chart" class="chart-container"></div>
		</view>
		<view>
			<uni-forms ref="form"  :modelValue="formData">
				<view class="uni-list sk-div">
					<view class="uni-list-cell">
						<uni-section title="本地数据" type="line">
							<view class="uni-px-5 uni-pb-5">
								<uni-data-select v-model="selected" :localdata="dataList" @change="onDataSelectChange">
									
								</uni-data-select>
							</view>
						</uni-section>
					</view>

					<view class="button-group sk-btdiv">
						<button class="sk-bt" type="primary" size="mini" @click="formSubmit">
							RUN
						</button>
					</view>
				</view>
			</uni-forms>
		</view>

		<view style="padding-bottom: 50px;">
			<view class="uni-container">
				<uni-table ref="table" :loading="loading" border stripe emptyText="暂无更多数据"
					@selection-change="selectionChange">
					<uni-tr>
						<uni-th width="40" align="center">買入日</uni-th>
						<uni-th width="40" align="center">価</uni-th>
						<uni-th width="40" align="center">賣出日</uni-th>
						<uni-th width="40" align="center">価</uni-th>
						<uni-th width="20" align="center">倉位</uni-th>
						<uni-th width="20" align="center">盈利</uni-th>
					</uni-tr>
					<uni-tr v-for="(item, index) in tableData" :key="index">
						<uni-td>{{ item.buyDate }}</uni-td>
						<uni-td>{{ item.buyPrice }}</uni-td>
						<uni-td>{{ item.sellDate }}</uni-td>
						<uni-td>{{ item.sellPrice }}</uni-td>
						<uni-td align="right">{{ item.warehousePosition }}</uni-td>
						<uni-td align="right">{{ item.profitMargin }}</uni-td>
					</uni-tr>
				</uni-table>

			</view>
		</view>

		<vive class="goods-carts goods-carts2">
			<uni-goods-nav :options="options" :buttonGroup="buttonGroup" @click="onClick" @buttonClick="buttonClick" />
		</vive>
	</view>
</template>

<script>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useSkLogic } from './skLogic'
import { SK_CONSTANTS } from './skConstants'
import uniTable from '@dcloudio/uni-ui/lib/uni-table/uni-table.vue'
import uniTr from '@dcloudio/uni-ui/lib/uni-tr/uni-tr.vue'
import uniTh from '@dcloudio/uni-ui/lib/uni-th/uni-th.vue'
import uniTd from '@dcloudio/uni-ui/lib/uni-td/uni-td.vue'
import uniPagination from '@dcloudio/uni-ui/lib/uni-pagination/uni-pagination.vue'
import uniDataSelect from '@dcloudio/uni-ui/lib/uni-data-select/uni-data-select.vue'
import getStrategy from '@/services/sk/getStrategy.js'
import getHuiceData from '@/services/sk/getHuice.js'
import { addToWatchlist, removeFromWatchlist } from '@/services/sk/watchlist.js'
import { useRoute } from 'vue-router';
import uniIcons from '@dcloudio/uni-ui/lib/uni-icons/uni-icons.vue';
import uniGoodsNav from '@dcloudio/uni-ui/lib/uni-goods-nav/uni-goods-nav.vue';


export default {
	name: 'SkPage',
	components: {
		uniTable,
		uniTr,
		uniTh,
		uniTd,
		uniPagination,
		uniDataSelect,
		uniIcons,
		uniGoodsNav
	},
	setup() {
		// inputParms  
		const route = useRoute();

		const { resize } = useSkLogic()
		// 下拉框
		const dataList = ref([])
		const selected = ref(0)

		// 表格相关的响应式数据
		const loading = ref(false)
		const tableData = ref([])

		// 关注list
		const guanzhuList = ref([])

		// 按钮组（将按钮状态放到 setup 中以便动态更新）
		const buttonGroup = ref([
			{
				text: '測試',
				backgroundColor: '#ff0000',
				color: '#fff'
			},
			{
				text: '加入自選',
				backgroundColor: '#ffa200',
				color: '#fff'
			}
		])

		// 加载表格数据的方法
		const loadTableData = async () => {
			try {
				loading.value = true
				const r = await getHuiceData(route.query.skId, selected.value)
				console.log('getHuiceData:', r); // 调试输出
				tableData.value = r.data.historyList

				// mack数据更新
				const { updateEcharts } = useSkLogic()
				await updateEcharts(r)
				console.log('sk chart update')

			} catch (e) {
				console.error('表格数据加载失败', e)
			} finally {
				loading.value = false
			}
		}

		// 表格相关的方法
		function selectionChange(e) {
			console.log('选中的数据', e.detail.index)
		}


		const formSubmit = async (praams) => {
			await loadTableData()
		}

		function resizeHandler() {
			resize()
		}

		function bindPickerChange(e) {
			index.value = e.detail.value
		}

		function onDataSelectChange(val) {

		}

		onMounted(async () => {

			// add resize listener for responsiveness
			window.addEventListener('resize', resizeHandler)

			// 1 使用 getStrategy 加载下拉框数据
			try {
				const strategy = await getStrategy()
				console.log('strategy:', strategy.data);
				guanzhuList.value = strategy.guanzhuList
				if (strategy.data && Array.isArray(strategy.data)) {
					dataList.value = strategy.data
					selected.value = dataList.value.length > 0 ? dataList.value[0].value : null
				} 
				
				// 根据 route.query.skId 判断当前是否已在关注列表中，更新按钮文字
				const curId = route.query.skId
				// 打印调试信息，便于后端返回的 guanzhuList 与前端路由参数核对
				console.log('route.query.skId:', curId)
				console.log('guanzhuList from strategy:', guanzhuList.value)

				// 归一化比较：去掉非字母数字字符并转大写，便于匹配类似 "000811.SZ" 与 "000811sz"
				const strip = (s) => (s || '').toString().toUpperCase().replace(/[^A-Z0-9]/g, '')
				const cur6 = strip(curId).slice(0, 6)
				// 构建归一化后的关注列表（前6位）
				const normalizedGuanzhu = (guanzhuList.value || []).map(item => strip(item).slice(0, 6))
				console.log('normalized cur6:', cur6)
				console.log('normalized guanzhu list (first6):', normalizedGuanzhu)
				const found = normalizedGuanzhu.includes(cur6)
				console.log('matched in guanzhuList:', found)
				if (found) {
					buttonGroup.value[1].text = '取消自選'
				} else {
					buttonGroup.value[1].text = '加入自選'
				}
			} catch (e) {
				console.error('下拉框数据加载失败', e)
			}

			// 2 init chart and render with data from service/mock
			const { initAndRender } = useSkLogic()
			
			try {
				await initAndRender(SK_CONSTANTS.CHART_CONTAINER_ID,{skId: route.query.skId})
				console.log('sk chart initialized')
			} catch (e) {
				console.error('Failed to initialize sk chart:', e)
			}
			// 3 加载表格数据
			//await loadTableData()

			// 4 建立 WebSocket 连接
			// const socket = new WebSocket('ws://localhost:8080'); // 使用 mock 服务器地址

			// socket.onopen = () => {
			// 	console.log('WebSocket connection established')
			// 	// 发送初始化请求
			// 	socket.send(JSON.stringify({ action: 'subscribe', skId: route.query.skId }))
			// }

			// socket.onmessage = (event) => {
			// 	const data = JSON.parse(event.data)
			// 	console.log('WebSocket received data:', data)
			// 	// 更新表格数据
			// 	tableData.value = data.historyList
			// }

			// socket.onerror = (error) => {
			// 	console.error('WebSocket error:', error)
			// }

			// socket.onclose = () => {
			// 	console.log('WebSocket connection closed')
			// }

			// 保存 WebSocket 对象以便在卸载组件时关闭连接
			return () => {
				socket.close()
			}
		})

		onBeforeUnmount(() => {
			window.removeEventListener('resize', resizeHandler)
		})

		return {
			bindPickerChange,
			// uni-data-select mock data + selected
			dataList,
			selected,
			onDataSelectChange,
			// 表格相关的数据
			loading,
			tableData,
			selectionChange,
			formSubmit,
			buttonGroup,
			guanzhuList
		}
	},

	// keep uni-app onLoad lifecycle to receive navigation params
	async onLoad(option) {
	},
	
	data () {
	  return {
	    options: [
			// {
			// icon: 'contact',
			// text: '客服'
			// }
		]
	  }
	},
	methods: {
	  async onClick (e) {
			try {
				console.log('onClick event:', e)
				uni.showToast({ title: `点击${e && e.content ? e.content.text : ''}`, icon: 'none' })
				// 如果点击的是第二个按钮（加入/取消自選），根据当前文字决定调用添加或删除接口
				const secondText = this.buttonGroup && this.buttonGroup[1] && this.buttonGroup[1].text
				console.log('secondText:', secondText)
				if (e && e.content && e.content.text && e.content.text === secondText) {
					const rawId = (this.$route && this.$route.query && this.$route.query.skId) || ''
					const stock_code = (rawId || '').toString().replace(/[^0-9]/g, '').slice(0,6)
					console.log('rawId, stock_code:', rawId, stock_code)
					if (!stock_code) return
					if (secondText === '加入自選') {
						const resp = await addToWatchlist(stock_code)
						console.log('addToWatchlist resp:', resp)
						if (resp && (resp.code === 0 || resp.success === true || resp.status === 'ok')) {
							if (Array.isArray(this.guanzhuList)) this.guanzhuList.push(stock_code)
							if (this.buttonGroup && this.buttonGroup[1]) this.buttonGroup[1].text = '取消自選'
							uni.showToast({ title: '已加入自選', icon: 'success' })
						} else {
							uni.showToast({ title: (resp && resp.message) || '加入失败', icon: 'none' })
						}
					} else if (secondText === '取消自選') {
						const resp = await removeFromWatchlist(stock_code)
						console.log('removeFromWatchlist resp:', resp)
						if (resp && (resp.code === 0 || resp.success === true)) {
							if (Array.isArray(this.guanzhuList)) {
								const idx = this.guanzhuList.findIndex(x => (x || '').toString().slice(0,6) === stock_code)
								if (idx >= 0) this.guanzhuList.splice(idx, 1)
							}
							if (this.buttonGroup && this.buttonGroup[1]) this.buttonGroup[1].text = '加入自選'
							uni.showToast({ title: '已取消自選', icon: 'success' })
						} else {
							uni.showToast({ title: (resp && resp.message) || '取消失败', icon: 'none' })
						}
					}
				}
			} catch (err) {
				console.error('watchlist action failed', err)
				uni.showToast({ title: '操作失败', icon: 'none' })
			}
	  },
	  buttonClick (e) {
	    console.log('buttonClick event:', e)
	    // 只有当点击的按钮文本等于第二个按钮（加入/取消自選）时，才触发 onClick 处理逻辑
	    try {
	      const clickedText = e && e.content && e.content.text
	      const secondText = this.buttonGroup && this.buttonGroup[1] && this.buttonGroup[1].text
	      if (clickedText && secondText && clickedText === secondText) {
	        // 转发到 onClick，保持原有行为（包含后端调用及 UI 更新）
	        this.onClick(e)
	      } else {
	        console.log('buttonClick ignored, clickedText:', clickedText)
	      }
	    } catch (err) {
	      console.error('buttonClick handler error', err)
	    }
	  }
	}

}
</script>

<style lang="scss">
.chart-container {
	width: 100%;
	height: 60vh;
	/* fits full viewport height; adjust as needed */
}

.page {
	width: 100%;
	height: 100%;
}

.sk-div {
	padding: 8px 8px 8px 8px;
}

.sk-btdiv {
	padding: 16px 0 8px 0;
}

.sk-bt {
	width: 100%;
}

.goods-carts {
	/* #ifndef APP-NVUE */
	display: flex;
	/* #endif */
	flex-direction: column;
	position: fixed;
	left: 0;
	right: 0;
	/* #ifdef H5 */
	left: var(--window-left);
	right: var(--window-right);
	/* #endif */
	bottom: 0;
}

.goods-carts2 ::v-deep .uni-tab__cart-sub-left {
  padding:0 0;
}
  
</style>
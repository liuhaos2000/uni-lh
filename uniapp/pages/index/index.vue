<template>
	<view>
		<view class="page-body">
			<view class="btn-area">
				<!-- 使用绝对路径（以 / 开头），否则在某些运行环境下会被解析为相对路径而无法跳转 -->
				<navigator animation-type="slide-out-right" url="/pages/sk/sk?skId=600001" hover-class="navigator-hover">
					<button type="default">SK</button>
				</navigator>
	
				<!-- 程序化跳转测试按钮（直接调用 uni.navigateTo） -->
				<button type="default" @click="goToMain" @tap="goToMain">程序化跳转测试</button>
				<!-- redirect 会在当前页替换为目标页，使用绝对路径 -->
				<navigator url="/pages/main/main01/main01" open-type="redirect" hover-class="other-navigator-hover">
					<button type="default">在当前页打开</button>
				</navigator>
				<!-- switchTab 只能用于跳转到 tabBar 页面；如果目标不是 tab，请改用 navigate/redirect 等 -->
				<navigator url="/pages/main/main01/main01" hover-class="other-navigator-hover">
					<button type="default">跳转到新页面（非 tab）</button>
				</navigator>
			</view>
		</view>
	</view>
</template>
<script>
// navigate.vue页面接受参数
export default {
	onLoad: function (option) { // option 为 object 类型，会序列化上个页面传递的参数

	},
	methods: {
		// programmatic navigation for diagnostics
		goToMain() {
			console.log('goToMain called')
			try {
				uni.navigateTo({
					url: '/pages/main/main01/main01',
					success() {
						console.log('navigateTo success')
					},
					fail(err) {
						console.error('navigateTo fail', err)
					}
				})
			} catch (e) {
				console.error('navigateTo exception', e)
			}
		}
	}
}
</script>

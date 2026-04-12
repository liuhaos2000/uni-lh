<script>
	export default {
		onLaunch: function() {
			console.log('App Launch')
		},
		onShow: function() {
			console.log('App Show')
		},
		onHide: function() {
			console.log('App Hide')
		}
	}
</script>

<style>
	/*每个页面公共css */

	/* 修复 iOS 真机 input 无法聚焦 / 无法输入 */
	input,
	textarea,
	.uni-input-input,
	.uni-textarea-textarea {
		-webkit-user-select: text !important;
		user-select: text !important;
	}

	/* 禁止双击放大（iOS 10+ 忽略 viewport user-scalable=no，需用 CSS） */
	page,
	body,
	uni-page-body {
		touch-action: manipulation;
	}
</style>

<template>
	<view class="auth-container">
		<view class="auth-card">
			<view class="auth-title">登录</view>
			<view class="auth-subtitle">动量轮动策略助手</view>

			<view class="form-item">
				<text class="form-label">邮箱</text>
				<input class="form-input" v-model="email" placeholder="注册时填写的邮箱" maxlength="60" />
			</view>

			<view class="form-item">
				<text class="form-label">密码</text>
				<input class="form-input" type="password" v-model="password" placeholder="6-60位" maxlength="60" />
			</view>

			<view class="form-item form-item-with-addon">
				<text class="form-label">图形验证码</text>
				<input class="form-input form-input-pad" v-model="captchaText" placeholder="点击图片刷新" maxlength="6" />
				<image v-if="captchaImage" class="addon-img" :src="captchaImage" mode="aspectFit" @click="refreshCaptcha" />
				<view v-else class="addon-img addon-placeholder" @click="refreshCaptcha">点击加载</view>
			</view>

			<button class="primary-btn" type="primary" :loading="loading" @click="onLogin">登录</button>

			<view class="auth-links">
				<text class="link" @click="goRegister">还没账号？去注册</text>
				<text class="link link-right" @click="goForgot">忘记密码？</text>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { loginApi, getCaptchaApi } from '@/services/auth/authService.js'
import userStore from '@/stores/user.js'

const email = ref('')
const password = ref('')
const captchaText = ref('')
const captchaId = ref('')
const captchaImage = ref('')
const loading = ref(false)

const refreshCaptcha = async () => {
	captchaText.value = ''
	try {
		const res = await getCaptchaApi()
		if (res && res.code === 0) {
			captchaId.value = res.data.captcha_id
			captchaImage.value = res.data.image_base64
			if (!captchaImage.value && res.data.fallback_text) {
				uni.showToast({ title: '后端缺 Pillow，调试码：' + res.data.fallback_text, icon: 'none', duration: 4000 })
			}
		}
	} catch (e) {
		uni.showToast({ title: '验证码加载失败', icon: 'none' })
	}
}

const onLogin = async () => {
	if (!email.value.trim() || !password.value) {
		uni.showToast({ title: '请填写邮箱和密码', icon: 'none' })
		return
	}
	if (!captchaText.value) {
		uni.showToast({ title: '请填写图形验证码', icon: 'none' })
		return
	}
	loading.value = true
	try {
		const res = await loginApi({
			email: email.value.trim(),
			password: password.value,
			captcha_id: captchaId.value,
			captcha_text: captchaText.value.trim(),
		})
		if (res && res.code === 0) {
			userStore.setAuth({
				access: res.data.access,
				refresh: res.data.refresh,
				user: res.data.user,
			})
			uni.showToast({ title: '登录成功', icon: 'success' })
			setTimeout(() => {
				const pages = getCurrentPages()
				if (pages.length > 1) {
					uni.navigateBack()
				} else {
					uni.switchTab({
						url: '/pages/index/index',
						fail: () => uni.reLaunch({ url: '/pages/index/index' }),
					})
				}
			}, 300)
		} else {
			uni.showToast({ title: (res && res.message) || '登录失败', icon: 'none' })
			refreshCaptcha()
		}
	} catch (e) {
		const msg = (e && e.res && e.res.data && e.res.data.message) || (e && e.message) || '网络错误'
		uni.showToast({ title: msg, icon: 'none' })
		refreshCaptcha()
	} finally {
		loading.value = false
	}
}

const goRegister = () => {
	uni.redirectTo({ url: '/pages/auth/register' })
}

const goForgot = () => {
	uni.navigateTo({ url: '/pages/auth/forgot' })
}

onMounted(() => {
	refreshCaptcha()
})
</script>

<style>
.auth-container {
	min-height: 100vh;
	background: #f5f6fa;
	padding: 40px 20px;
	box-sizing: border-box;
}

.auth-card {
	width: 100%;
	max-width: 420px;
	margin: 0 auto;
	background: #fff;
	border-radius: 12px;
	padding: 32px 24px;
	box-sizing: border-box;
	box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}

.auth-title {
	font-size: 24px;
	font-weight: 600;
	color: #222;
	text-align: center;
}

.auth-subtitle {
	font-size: 13px;
	color: #999;
	text-align: center;
	margin-top: 6px;
	margin-bottom: 28px;
}

.form-item {
	margin-bottom: 16px;
}

.form-label {
	display: block;
	font-size: 13px;
	color: #666;
	margin-bottom: 6px;
}

.form-input {
	display: block;
	width: 100%;
	height: 44px;
	line-height: 24px;
	border: 1px solid #e0e0e0;
	border-radius: 6px;
	padding: 10px 12px;
	font-size: 16px;
	background: #fafafa;
	box-sizing: border-box;
}

/* 输入框右侧带验证码图片 */
.form-item-with-addon {
	position: relative;
}

.form-input-pad {
	padding-right: 130rpx;
}

.addon-img {
	position: absolute;
	right: 6rpx;
	bottom: 6rpx;
	width: 220rpx;
	height: 64rpx;
	border-radius: 6px;
	border: 1px solid #e0e0e0;
	background: #fff;
}

.addon-placeholder {
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 12px;
	color: #999;
}

.primary-btn {
	width: 100%;
	margin-top: 12px;
}

.auth-links {
	margin-top: 18px;
	display: flex;
	flex-direction: row;
	justify-content: space-between;
	align-items: center;
}

.link {
	font-size: 13px;
	color: #5470c6;
}

.link-right {
	color: #888;
}
</style>

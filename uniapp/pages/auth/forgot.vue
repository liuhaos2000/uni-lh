<template>
	<view class="auth-container">
		<view class="auth-card">
			<view class="auth-title">找回密码</view>
			<view class="auth-subtitle">通过邮箱验证码重置密码</view>

			<view class="form-item">
				<text class="form-label">邮箱</text>
				<input class="form-input" v-model="email" placeholder="注册时填写的邮箱" maxlength="60" />
			</view>

			<view class="form-item form-item-with-addon">
				<text class="form-label">图形验证码</text>
				<input class="form-input form-input-pad" v-model="captchaText" placeholder="点击图片刷新" maxlength="6" />
				<image v-if="captchaImage" class="addon-img" :src="captchaImage" mode="aspectFit" @click="refreshCaptcha" />
				<view v-else class="addon-img addon-placeholder" @click="refreshCaptcha">点击加载</view>
			</view>

			<view class="form-item form-item-with-addon">
				<text class="form-label">邮箱验证码</text>
				<input class="form-input form-input-pad" v-model="emailCode" placeholder="6 位数字" maxlength="6" />
				<button class="addon-btn" :disabled="cdLeft > 0 || sending" @click="onSendCode">
					{{ cdLeft > 0 ? `${cdLeft}s` : '发送验证码' }}
				</button>
			</view>

			<view class="form-item">
				<text class="form-label">新密码</text>
				<input class="form-input" type="password" v-model="password" placeholder="6-60位" maxlength="60" />
			</view>

			<view class="form-item">
				<text class="form-label">确认新密码</text>
				<input class="form-input" type="password" v-model="password2" placeholder="再次输入新密码" maxlength="60" />
			</view>

			<button class="primary-btn" type="primary" :loading="loading" @click="onReset">重置密码</button>

			<view class="auth-links">
				<text class="link" @click="goLogin">返回登录</text>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import {
	getCaptchaApi,
	sendEmailCodeApi,
	resetPasswordApi,
} from '@/services/auth/authService.js'

const email = ref('')
const password = ref('')
const password2 = ref('')
const emailCode = ref('')
const captchaText = ref('')
const captchaId = ref('')
const captchaImage = ref('')

const sending = ref(false)
const loading = ref(false)
const cdLeft = ref(0)
let cdTimer = null

const EMAIL_RE = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/

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

const startCountdown = (sec = 60) => {
	cdLeft.value = sec
	if (cdTimer) clearInterval(cdTimer)
	cdTimer = setInterval(() => {
		cdLeft.value -= 1
		if (cdLeft.value <= 0) {
			clearInterval(cdTimer)
			cdTimer = null
		}
	}, 1000)
}

const onSendCode = async () => {
	if (!EMAIL_RE.test(email.value.trim())) {
		uni.showToast({ title: '请输入正确邮箱', icon: 'none' })
		return
	}
	if (!captchaText.value) {
		uni.showToast({ title: '请先填写图形验证码', icon: 'none' })
		return
	}
	sending.value = true
	try {
		const res = await sendEmailCodeApi({
			email: email.value.trim(),
			captcha_id: captchaId.value,
			captcha_text: captchaText.value.trim(),
			purpose: 'reset',
		})
		if (res && res.code === 0) {
			uni.showToast({ title: '验证码已发送', icon: 'success' })
			startCountdown(60)
		} else {
			uni.showToast({ title: (res && res.message) || '发送失败', icon: 'none' })
			refreshCaptcha()
		}
	} catch (e) {
		const msg = (e && e.res && e.res.data && e.res.data.message) || (e && e.message) || '网络错误'
		uni.showToast({ title: msg, icon: 'none' })
		refreshCaptcha()
	} finally {
		sending.value = false
	}
}

const onReset = async () => {
	const em = email.value.trim()
	if (!EMAIL_RE.test(em)) {
		uni.showToast({ title: '请输入正确邮箱', icon: 'none' })
		return
	}
	if (password.value.length < 6) {
		uni.showToast({ title: '密码至少 6 位', icon: 'none' })
		return
	}
	if (password.value !== password2.value) {
		uni.showToast({ title: '两次密码不一致', icon: 'none' })
		return
	}
	if (!captchaText.value || !emailCode.value) {
		uni.showToast({ title: '请填写图形验证码与邮箱验证码', icon: 'none' })
		return
	}

	loading.value = true
	try {
		const res = await resetPasswordApi({
			email: em,
			email_code: emailCode.value.trim(),
			new_password: password.value,
			captcha_id: captchaId.value,
			captcha_text: captchaText.value.trim(),
		})
		if (res && res.code === 0) {
			uni.showToast({ title: '密码已重置', icon: 'success' })
			setTimeout(() => {
				uni.redirectTo({ url: '/pages/auth/login' })
			}, 600)
		} else {
			uni.showToast({ title: (res && res.message) || '重置失败', icon: 'none' })
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

const goLogin = () => {
	uni.redirectTo({ url: '/pages/auth/login' })
}

onMounted(() => {
	refreshCaptcha()
})

onUnmounted(() => {
	if (cdTimer) clearInterval(cdTimer)
})
</script>

<style>
.auth-container {
	min-height: 100vh;
	background: #f5f6fa;
	padding: 30px 20px;
	box-sizing: border-box;
}

.auth-card {
	width: 100%;
	max-width: 420px;
	margin: 0 auto;
	background: #fff;
	border-radius: 12px;
	padding: 28px 22px;
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
	margin-bottom: 22px;
}

.form-item {
	margin-bottom: 14px;
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

/* 输入框右侧带验证码图片或按钮 */
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

.addon-btn {
	position: absolute;
	right: 4rpx;
	bottom: 4rpx;
	height: 68rpx;
	line-height: 68rpx;
	min-width: 220rpx;
	font-size: 13px;
	background: #5470c6;
	color: #fff;
	border-radius: 6px;
	padding: 0 16rpx;
	margin: 0;
}

.addon-btn[disabled] {
	background: #c2c8d6;
	color: #fff;
}

.primary-btn {
	width: 100%;
	margin-top: 12px;
}

.auth-links {
	margin-top: 18px;
	text-align: center;
}

.link {
	font-size: 13px;
	color: #5470c6;
}
</style>

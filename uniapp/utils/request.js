/**
 * 全局 uni.request 封装
 *
 * - 自动拼接 BASE_URL
 * - 自动附带 Authorization: Bearer <token>
 * - 401 时自动用 refresh token 续期，续期失败才跳登录页
 */
import ENV from '@/config/env.js'

const TOKEN_KEY = 'auth_access_token'
const REFRESH_KEY = 'auth_refresh_token'
const USER_KEY = 'auth_user'

export const tokenStore = {
  getAccess() {
    try { return uni.getStorageSync(TOKEN_KEY) || '' } catch (e) { return '' }
  },
  getRefresh() {
    try { return uni.getStorageSync(REFRESH_KEY) || '' } catch (e) { return '' }
  },
  getUser() {
    try { return uni.getStorageSync(USER_KEY) || null } catch (e) { return null }
  },
  set({ access, refresh, user }) {
    if (access !== undefined) uni.setStorageSync(TOKEN_KEY, access || '')
    if (refresh !== undefined) uni.setStorageSync(REFRESH_KEY, refresh || '')
    if (user !== undefined) uni.setStorageSync(USER_KEY, user || null)
  },
  clear() {
    uni.removeStorageSync(TOKEN_KEY)
    uni.removeStorageSync(REFRESH_KEY)
    uni.removeStorageSync(USER_KEY)
  },
}

let redirecting = false
const redirectToLogin = () => {
  if (redirecting) return
  redirecting = true
  tokenStore.clear()
  setTimeout(() => { redirecting = false }, 1500)
  uni.showToast({ title: '请先登录', icon: 'none' })
  setTimeout(() => {
    uni.navigateTo({ url: '/pages/auth/login' })
  }, 300)
}

// refresh token 续期（防止并发重复刷新）
let refreshing = null

function doRefresh() {
  if (refreshing) return refreshing
  const refresh = tokenStore.getRefresh()
  if (!refresh) return Promise.reject()

  refreshing = new Promise((resolve, reject) => {
    uni.request({
      url: `${ENV.API.BASE_URL}/auth/refresh/`,
      method: 'POST',
      header: { 'Content-Type': 'application/json' },
      data: { refresh },
      success: (res) => {
        if (res.statusCode === 200 && res.data && res.data.access) {
          tokenStore.set({ access: res.data.access })
          resolve(res.data.access)
        } else {
          reject()
        }
      },
      fail: () => reject(),
    })
  }).finally(() => { refreshing = null })

  return refreshing
}

/**
 * 发起请求
 */
export function request(options) {
  const {
    url,
    method = 'GET',
    data,
    header = {},
    auth = true,
    silent = false,
    timeout = ENV.API.TIMEOUT,
    _retried = false,
  } = options

  const fullUrl = /^https?:\/\//.test(url) ? url : `${ENV.API.BASE_URL}${url}`
  const finalHeader = { 'Content-Type': 'application/json', ...header }
  if (auth) {
    const token = tokenStore.getAccess()
    if (token) finalHeader['Authorization'] = `Bearer ${token}`
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: fullUrl,
      method,
      data,
      header: finalHeader,
      timeout,
      success: (res) => {
        if (res.statusCode === 401 && auth && !_retried) {
          // 尝试用 refresh token 续期
          doRefresh().then((newToken) => {
            // 用新 token 重试原请求
            request({ ...options, _retried: true }).then(resolve).catch(reject)
          }).catch(() => {
            if (!silent) redirectToLogin()
            reject({ code: 401, message: '未登录或登录已过期', res })
          })
          return
        }
        if (res.statusCode === 401) {
          if (!silent) redirectToLogin()
          reject({ code: 401, message: '未登录或登录已过期', res })
          return
        }
        resolve(res.data)
      },
      fail: (err) => reject(err),
    })
  })
}

export default request

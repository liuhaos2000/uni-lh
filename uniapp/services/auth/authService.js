/**
 * 认证服务：图形验证码 / 邮箱验证码 / 注册 / 登录 / 找回密码 / 当前用户
 */
import request from '@/utils/request.js'

export const getCaptchaApi = () =>
  request({
    url: '/auth/captcha/',
    method: 'GET',
    auth: false,
  })

export const sendEmailCodeApi = (payload) =>
  request({
    url: '/auth/send-code/',
    method: 'POST',
    data: payload,
    auth: false,
  })

export const registerApi = (payload) =>
  request({
    url: '/auth/register/',
    method: 'POST',
    data: payload,
    auth: false,
  })

export const loginApi = (payload) =>
  request({
    url: '/auth/login/',
    method: 'POST',
    data: payload,
    auth: false,
  })

export const resetPasswordApi = (payload) =>
  request({
    url: '/auth/reset-password/',
    method: 'POST',
    data: payload,
    auth: false,
  })

export const meApi = () =>
  request({
    url: '/auth/me/',
    method: 'GET',
    silent: true,
  })

export default {
  getCaptchaApi,
  sendEmailCodeApi,
  registerApi,
  loginApi,
  resetPasswordApi,
  meApi,
}

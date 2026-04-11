/**
 * 轻量响应式 user store
 * 不引入 pinia，使用 Vue 3 的 reactive。
 */
import { reactive, computed } from 'vue'
import { tokenStore } from '@/utils/request.js'

const state = reactive({
  user: tokenStore.getUser(),
  token: tokenStore.getAccess(),
})

export const userStore = {
  state,
  isLoggedIn: computed(() => !!state.token),

  setAuth({ access, refresh, user }) {
    state.token = access || ''
    state.user = user || null
    tokenStore.set({ access, refresh, user })
  },

  setUser(user) {
    state.user = user || null
    tokenStore.set({ user })
  },

  logout() {
    state.token = ''
    state.user = null
    tokenStore.clear()
  },
}

export default userStore

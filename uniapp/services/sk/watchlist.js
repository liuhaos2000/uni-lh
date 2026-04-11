import request from '@/utils/request.js'

export const addToWatchlist = (stock_code) =>
  request({ url: '/sk/add/', method: 'POST', data: { stock_code } })

export const removeFromWatchlist = (stock_code) =>
  request({ url: '/sk/remove/', method: 'POST', data: { stock_code } })

export default { addToWatchlist, removeFromWatchlist }

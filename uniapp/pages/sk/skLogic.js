import { onMounted, onBeforeUnmount, ref } from 'vue'
import { getSkInitData } from '@/services/sk'
import { SK_CONSTANTS } from './skConstants'

let chart = null

// Load echarts with dynamic import and CDN fallback (same approach as before)
async function loadEcharts() {
  try {
    const mod = await import(/* @vite-ignore */ 'echarts')
    return mod.default || mod
  } catch (err) {
    if (typeof window !== 'undefined' && window.echarts) return window.echarts
    await new Promise((resolve, reject) => {
      const s = document.createElement('script')
      s.src = 'https://fastly.jsdelivr.net/npm/echarts@5/dist/echarts.min.js'
      s.onload = () => resolve()
      s.onerror = (e) => reject(e)
      document.head.appendChild(s)
    })
    return window.echarts
  }
}

function splitData(rawData) {
  const categoryData = []
  const values = []
  for (let i = 0; i < rawData.length; i++) {
    const item = rawData[i].slice()
    categoryData.push(item.splice(0, 1)[0])
    values.push(item)
  }
  return { categoryData, values }
}

function calculateMA(values, dayCount) {
  const result = []
  for (let i = 0, len = values.length; i < len; i++) {
    if (i < dayCount) {
      result.push('-')
      continue
    }
    let sum = 0
    for (let j = 0; j < dayCount; j++) {
      sum += +values[i - j][1]
    }
    result.push(sum / dayCount)
  }
  return result
}

export function useSkLogic() {
  const loading = ref(false)

  async function initAndRender(containerId, optionParams = {}) {



    loading.value = true
    try {
      const echarts = await loadEcharts()
      const dom = document.getElementById(containerId || SK_CONSTANTS.CHART_CONTAINER_ID)
      if (!dom) throw new Error('chart container not found: ' + containerId)

      chart = echarts.init(dom, null, SK_CONSTANTS.CHART_DEFAULTS)

      // fetch init data from service
      const initData = await getSkInitData(optionParams.skId)

      // initData should include a `raw` array like in the original example
      const raw = initData.data.raw || []
      const data0 = splitData(raw)

      const upColor = '#ec0000'
      const upBorderColor = '#8A0000'
      const downColor = '#00da3c'
      const downBorderColor = '#008F28'

      const option = {
        title: { text: initData.data.title || '上证指数', left: 0 },
        tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
        legend: { data: ['日K', 'MA5', 'MA10', 'MA20', 'MA30'], top: 50 },
        grid: { left: '10%', right: '10%', bottom: '15%' ,top:90},
        xAxis: {
          type: 'category',
          data: data0.categoryData,
          boundaryGap: false,
          axisLine: { onZero: false },
          splitLine: { show: false },
          min: 'dataMin',
          max: 'dataMax'
        },
        yAxis: { scale: true, splitArea: { show: true } },
        dataZoom: initData.data.dataZoom || [ { type: 'inside', start: 50, end: 100 }, { show: true, type: 'slider', top: '90%', start: 50, end: 100 } ],
        series: [
          {
            name: '日K',
            type: 'candlestick',
            data: data0.values,
            itemStyle: {
              color: upColor,
              color0: downColor,
              borderColor: upBorderColor,
              borderColor0: downBorderColor
            }
          },
          { name:  'MA5', type: 'line', data: calculateMA(data0.values,  5), smooth: true, lineStyle: { opacity: 0.5 } },
          { name: 'MA10', type: 'line', data: calculateMA(data0.values, 10), smooth: true, lineStyle: { opacity: 0.5 } },
          { name: 'MA20', type: 'line', data: calculateMA(data0.values, 20), smooth: true, lineStyle: { opacity: 0.5 } },
          { name: 'MA30', type: 'line', data: calculateMA(data0.values, 30), smooth: true, lineStyle: { opacity: 0.5 } }
        ]
      }

      chart.setOption(option)
    } catch (e) {
      console.error('initAndRender error:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  function updateEcharts(initData) {

      const newOptions = {
        series: [
          {
            name: '日K',
            markPoint: initData.data.markPoint || {},
            markLine: initData.data.markLine || {}
          }
        ]
      }

    if (chart) {
      chart.setOption(newOptions, false)  // 第二个参数为 true 表示不合并配置，直接替换
    }
  }

  function resize() {
    if (chart && typeof chart.resize === 'function') chart.resize()
  }

  function dispose() {
    if (chart) {
      chart.dispose()
      chart = null
    }
  }

  // hook: ensure cleanup when logic's consumer unmounts
  onBeforeUnmount(() => {
    dispose()
  })

  return {
    loading,
    initAndRender,
    resize,
    dispose,
    updateEcharts
  }
}

import { onMounted, onBeforeUnmount, ref } from 'vue'
import { getSkInitData } from '@/services/sk'
import { SK_CONSTANTS } from './skConstants'

let chart = null

// 保存初始化时拿到的 K 线数据，供 updateEcharts 重建图表时复用
let storedCategories = []
let storedValues     = []
let storedTitle      = ''
let storedDataZoom   = null

// ─────────────────────────────────────────────
// 手动 touch 捏合缩放 + 单指平移
// ─────────────────────────────────────────────
let _touchCleanup = null

function attachTouchZoom(dom) {
  if (_touchCleanup) _touchCleanup()

  let startDist    = 0
  let startZoom    = { start: 50, end: 100 }
  let lastSingleX  = null
  let startSingleX = null
  let isDragging   = false

  function getZoomState() {
    if (!chart) return { start: 50, end: 100 }
    const opt = chart.getOption()
    const dz  = opt.dataZoom && opt.dataZoom[0]
    return dz ? { start: dz.start, end: dz.end } : { start: 50, end: 100 }
  }

  function pinchDist(t) {
    const dx = t[0].clientX - t[1].clientX
    const dy = t[0].clientY - t[1].clientY
    return Math.sqrt(dx * dx + dy * dy)
  }

  function onTouchStart(e) {
    if (e.touches.length === 2) {
      startDist = pinchDist(e.touches)
      startZoom = getZoomState()
      e.preventDefault()
    } else if (e.touches.length === 1) {
      lastSingleX  = e.touches[0].clientX
      startSingleX = e.touches[0].clientX
      isDragging   = false
    }
  }

  function onTouchMove(e) {
    if (e.touches.length === 2) {
      e.preventDefault()
      const newDist = pinchDist(e.touches)
      if (!startDist) return
      const ratio  = startDist / newDist           // <1 放大, >1 缩小
      const range  = startZoom.end - startZoom.start
      const newRange = Math.min(100, Math.max(5, range * ratio))
      const mid    = (startZoom.start + startZoom.end) / 2
      let   ns     = mid - newRange / 2
      let   ne     = mid + newRange / 2
      if (ns < 0)   { ne -= ns; ns = 0 }
      if (ne > 100) { ns -= (ne - 100); ne = 100 }
      chart && chart.dispatchAction({ type: 'dataZoom', dataZoomIndex: 0, start: Math.max(0, ns), end: Math.min(100, ne) })
    } else if (e.touches.length === 1 && lastSingleX !== null) {
      const cur     = e.touches[0].clientX
      const totalDx = Math.abs(cur - startSingleX)
      // 移动超过 5px 才判定为拖动平移
      if (totalDx > 5) isDragging = true
      if (!isDragging) return
      e.preventDefault()
      const dx = cur - lastSingleX
      lastSingleX  = cur
      const { start, end } = getZoomState()
      const range = end - start
      const shift = -(dx / dom.offsetWidth) * range
      let ns = start + shift
      let ne = end   + shift
      if (ns < 0)   { ne -= ns; ns = 0 }
      if (ne > 100) { ns -= (ne - 100); ne = 100 }
      chart && chart.dispatchAction({ type: 'dataZoom', dataZoomIndex: 0, start: Math.max(0, ns), end: Math.min(100, ne) })
    }
  }

  function onTouchEnd(e) {
    const wasTap = !isDragging && startSingleX !== null
    if (wasTap && e.changedTouches.length === 1) {
      const t    = e.changedTouches[0]
      const rect = dom.getBoundingClientRect()
      chart && chart.dispatchAction({
        type: 'showTip',
        x: t.clientX - rect.left,
        y: t.clientY - rect.top,
      })
    }
    startDist    = 0
    lastSingleX  = null
    startSingleX = null
    isDragging   = false
  }

  dom.addEventListener('touchstart', onTouchStart, { passive: false })
  dom.addEventListener('touchmove',  onTouchMove,  { passive: false })
  dom.addEventListener('touchend',   onTouchEnd)

  _touchCleanup = () => {
    dom.removeEventListener('touchstart', onTouchStart)
    dom.removeEventListener('touchmove',  onTouchMove)
    dom.removeEventListener('touchend',   onTouchEnd)
    _touchCleanup = null
  }
}

// ─────────────────────────────────────────────
// ECharts 加载（动态 import + CDN 兜底）
// ─────────────────────────────────────────────
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

// ─────────────────────────────────────────────
// 原始数据拆分：日期 / OHLC
// 后端顺序: [open, high, low, close]
// ECharts candlestick 期望: [open, close, low, high]
// ─────────────────────────────────────────────
function splitData(rawData) {
  const categoryData = []
  const values       = []
  for (let i = 0; i < rawData.length; i++) {
    const item = rawData[i].slice()
    categoryData.push(item.splice(0, 1)[0])
    const [open, high, low, close] = item
    values.push([open, close, low, high])
  }
  return { categoryData, values }
}

// ─────────────────────────────────────────────
// 默认 MA 计算（初始加载时使用，values[i][1] = close）
// ─────────────────────────────────────────────
function calculateMA(values, dayCount) {
  const result = []
  for (let i = 0, len = values.length; i < len; i++) {
    if (i < dayCount) { result.push('-'); continue }
    let sum = 0
    for (let j = 0; j < dayCount; j++) sum += +values[i - j][1]
    result.push(+(sum / dayCount).toFixed(4))
  }
  return result
}

// ─────────────────────────────────────────────
// 根据参数动态构建完整 ECharts option
// ─────────────────────────────────────────────
function buildChartOption({
  categories,
  values,
  title,
  dataZoom,
  mainIndicator,   // 后端返回的主图指标数据（含 type + series）
  subIndicator,    // 后端返回的附图指标数据（含 type + series）
  markPoint,
  markLine,
}) {
  const hasSub = !!(subIndicator?.series?.length > 0)

  const upColor        = '#ec0000'
  const upBorderColor  = '#8A0000'
  const downColor      = '#00da3c'
  const downBorderColor = '#008F28'

  // ── Grid ──
  // 主图：top=90px（留给 legend），高度 46%
  // 附图：从 72% 开始，高度 16%，底部留 8% 给 dataZoom 滑块
  const grid = hasSub
    ? [
        { left: '10%', right: '2%', top: 90,    height: '46%' },
        { left: '10%', right: '2%', top: '72%', height: '16%' },
      ]
    : [{ left: '10%', right: '2%', bottom: '15%', top: 90 }]

  // ── 标题（多标题：主标题 + 附图指标名） ──
  const titleConfig = hasSub
    ? [
        { text: title || '', left: 0 },
        {
          text: subIndicator.type,
          left: '10%',
          top: '69%',   // 紧贴附图上方
          textStyle: { fontSize: 11, color: '#888', fontWeight: 'normal' },
        },
      ]
    : { text: title || '', left: 0 }

  // ── X 轴 ──
  const xAxisBase = {
    type: 'category',
    data: categories,
    boundaryGap: false,
    axisLine: { onZero: false },
    splitLine: { show: false },
    min: 'dataMin',
    max: 'dataMax',
  }
  const xAxis = hasSub
    ? [
        { ...xAxisBase, gridIndex: 0, axisLabel: { show: false } },
        { ...xAxisBase, gridIndex: 1 },
      ]
    : [xAxisBase]

  // ── Y 轴 ──
  const yAxis = hasSub
    ? [
        { scale: true, gridIndex: 0, splitArea: { show: true } },
        { scale: true, gridIndex: 1, splitArea: { show: true } },
      ]
    : [{ scale: true, splitArea: { show: true } }]

  // ── 主图 series ──
  const xIdx = hasSub ? 0 : undefined
  const yIdx = hasSub ? 0 : undefined

  const series = [
    {
      name: '日K',
      type: 'candlestick',
      xAxisIndex: xIdx,
      yAxisIndex: yIdx,
      data: values,
      itemStyle: {
        color:        upColor,
        color0:       downColor,
        borderColor:  upBorderColor,
        borderColor0: downBorderColor,
      },
      markPoint: markPoint || {},
      markLine:  markLine  || {},
    },
  ]

  const legendNames = ['日K']

  if (mainIndicator?.series?.length > 0) {
    // 使用后端计算的指标线
    for (const s of mainIndicator.series) {
      series.push({
        name: s.name,
        type: 'line',
        xAxisIndex: xIdx,
        yAxisIndex: yIdx,
        data: s.data,
        smooth: true,
        showSymbol: false,
        lineStyle: { opacity: 0.7 },
      })
      legendNames.push(s.name)
    }
  } else {
    // 初始加载默认 MA5/10/20/30
    for (const p of [5, 10, 20, 30]) {
      series.push({
        name: `MA${p}`,
        type: 'line',
        xAxisIndex: xIdx,
        yAxisIndex: yIdx,
        data: calculateMA(values, p),
        smooth: true,
        showSymbol: false,
        lineStyle: { opacity: 0.5 },
      })
      legendNames.push(`MA${p}`)
    }
  }

  // ── 附图 series ──
  if (hasSub) {
    for (const s of subIndicator.series) {
      const isMACDBar = subIndicator.type === 'MACD' && s.name === 'MACD'
      series.push({
        name: s.name,
        type: isMACDBar ? 'bar' : 'line',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: s.data,
        smooth: !isMACDBar,
        showSymbol: false,
        ...(isMACDBar
          ? {
              itemStyle: {
                color: (params) => (params.value >= 0 ? '#ec0000' : '#00da3c'),
              },
            }
          : { lineStyle: { width: 1.5 } }),
      })
      legendNames.push(s.name)
    }
  }

  // ── DataZoom：如有附图则同步两个 X 轴，滑块固定在底部 ──
  const baseZoom = dataZoom || [
    { type: 'inside', start: 50, end: 100 },
    { show: true, type: 'slider', bottom: '1%', start: 50, end: 100 },
  ]
  const finalZoom = hasSub
    ? baseZoom.map((dz) => ({ ...dz, xAxisIndex: [0, 1] }))
    : baseZoom

  return {
    title:    titleConfig,
    tooltip:  { trigger: 'axis', triggerOn: 'mousemove|click', axisPointer: { type: 'cross' } },
    legend:   { data: legendNames, top: 50 },
    grid,
    xAxis,
    yAxis,
    dataZoom: finalZoom,
    series,
  }
}

// ─────────────────────────────────────────────
// Composable
// ─────────────────────────────────────────────
export function useSkLogic() {
  const loading = ref(false)

  async function initAndRender(containerId, optionParams = {}) {
    loading.value = true
    try {
      const echarts = await loadEcharts()
      const dom = document.getElementById(containerId || SK_CONSTANTS.CHART_CONTAINER_ID)
      if (!dom) throw new Error('chart container not found: ' + containerId)

      chart = echarts.init(dom, null, SK_CONSTANTS.CHART_DEFAULTS)

      const initData = await getSkInitData(optionParams.skId)
      const raw      = initData.data.raw || []
      const data0    = splitData(raw)

      // 保存供 updateEcharts 复用
      storedCategories = data0.categoryData
      storedValues     = data0.values
      storedTitle      = initData.data.title   || ''
      storedDataZoom   = initData.data.dataZoom || null

      // 初始加载：使用默认 MA，无附图
      const option = buildChartOption({
        categories:    storedCategories,
        values:        storedValues,
        title:         storedTitle,
        dataZoom:      storedDataZoom,
        mainIndicator: null,
        subIndicator:  null,
      })

      chart.setOption(option)
      attachTouchZoom(dom)
    } catch (e) {
      console.error('initAndRender error:', e)
      throw e
    } finally {
      loading.value = false
    }
  }

  // 回测结果回来后，用策略指标 + 买卖标记重新渲染
  function updateEcharts(huiceData) {
    if (!chart) return

    const indicators  = huiceData.data?.indicators || {}
    const markPoint   = huiceData.data?.markPoint  || {}
    const markLine    = huiceData.data?.markLine   || {}

    const option = buildChartOption({
      categories:    storedCategories,
      values:        storedValues,
      title:         storedTitle,
      dataZoom:      storedDataZoom,
      mainIndicator: indicators.mainIndicator || null,
      subIndicator:  indicators.subIndicator  || null,
      markPoint,
      markLine,
    })

    // notMerge=true：完整替换，避免旧附图残留
    chart.setOption(option, true)
  }

  function resize() {
    if (chart && typeof chart.resize === 'function') chart.resize()
  }

  function dispose() {
    if (_touchCleanup) _touchCleanup()
    if (chart) { chart.dispose(); chart = null }
  }

  onBeforeUnmount(() => dispose())

  return { loading, initAndRender, resize, dispose, updateEcharts }
}

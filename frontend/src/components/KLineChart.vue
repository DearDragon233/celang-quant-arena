<template>
  <div ref="chartEl" :style="{ height: height + 'px', width: '100%' }"></div>
</template>

<script setup>
// K 线图组件：蜡烛图 + MA5/10/20 + 成交量 + 买卖点标记（红涨绿跌）
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  bars: { type: Array, default: () => [] },
  trades: { type: Array, default: () => [] }, // [{date, price, side}]
  height: { type: Number, default: 420 },
})

const chartEl = ref()
let chart = null

function maCalc(closes, n) {
  const out = []
  let s = 0
  for (let i = 0; i < closes.length; i++) {
    s += closes[i]
    if (i >= n) s -= closes[i - n]
    out.push(i >= n - 1 ? +(s / n).toFixed(2) : null)
  }
  return out
}

function render() {
  if (!chart || !props.bars.length) return
  const dates = props.bars.map((b) => b.date)
  const kdata = props.bars.map((b) => [b.open, b.close, b.low, b.high])
  const vols = props.bars.map((b, i) => ({
    value: b.volume,
    itemStyle: { color: b.close >= b.open ? '#e0313155' : '#0ca67855' },
  }))
  const ma5 = maCalc(props.bars.map((b) => b.close), 5)
  const ma10 = maCalc(props.bars.map((b) => b.close), 10)
  const ma20 = maCalc(props.bars.map((b) => b.close), 20)

  const dateIdx = Object.fromEntries(dates.map((d, i) => [d, i]))
  const points = props.trades
    .filter((t) => dateIdx[t.date] !== undefined)
    .map((t) => ({
      value: [dateIdx[t.date], t.price],
      symbol: t.side === 'buy' ? 'triangle' : 'pin',
      symbolSize: 11,
      itemStyle: { color: t.side === 'buy' ? '#e03131' : '#0ca678' },
      symbolRotate: t.side === 'buy' ? 0 : 180,
    }))

  chart.setOption(
    {
      animation: false,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: 'rgba(16,29,51,0.92)',
        borderWidth: 0,
        textStyle: { color: '#e8edf5', fontSize: 12 },
      },
      grid: [
        { left: 60, right: 70, top: 30, height: '58%' },
        { left: 60, right: 70, top: '74%', height: '16%' },
      ],
      xAxis: [
        { type: 'category', data: dates, gridIndex: 0, boundaryGap: true, axisLine: { lineStyle: { color: '#c9d2e0' } }, axisLabel: { show: false } },
        { type: 'category', data: dates, gridIndex: 1, axisLine: { lineStyle: { color: '#c9d2e0' } }, axisLabel: { color: '#606266', fontSize: 11 } },
      ],
      yAxis: [
        {
          scale: true, gridIndex: 0, splitLine: { lineStyle: { color: '#eef1f6' } },
          axisLabel: { color: '#606266', fontSize: 11 },
        },
        { gridIndex: 1, splitLine: { show: false }, axisLabel: { show: false } },
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
        { type: 'slider', xAxisIndex: [0, 1], bottom: 4, height: 18, borderColor: '#e4e9f2' },
      ],
      series: [
        {
          name: 'K线', type: 'candlestick', data: kdata, xAxisIndex: 0, yAxisIndex: 0,
          itemStyle: { color: '#e03131', color0: '#0ca678', borderColor: '#e03131', borderColor0: '#0ca678' },
          markPoint: points.length
            ? {
                symbolSize: 1,
                data: points,
                label: { show: false },
              }
            : undefined,
        },
        { name: 'MA5', type: 'line', data: ma5, xAxisIndex: 0, yAxisIndex: 0, showSymbol: false, lineStyle: { width: 1, color: '#f0a020' } },
        { name: 'MA10', type: 'line', data: ma10, xAxisIndex: 0, yAxisIndex: 0, showSymbol: false, lineStyle: { width: 1, color: '#7c6cff' } },
        { name: 'MA20', type: 'line', data: ma20, xAxisIndex: 0, yAxisIndex: 0, showSymbol: false, lineStyle: { width: 1, color: '#9254de' } },
        { name: '成交量', type: 'bar', data: vols, xAxisIndex: 1, yAxisIndex: 1 },
      ],
    },
    true
  )
  chart.resize()
}

onMounted(() => {
  chart = echarts.init(chartEl.value)
  render()
  window.addEventListener('resize', () => chart?.resize())
})

watch(() => [props.bars, props.trades], render, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', () => chart?.resize())
  chart?.dispose()
})
</script>

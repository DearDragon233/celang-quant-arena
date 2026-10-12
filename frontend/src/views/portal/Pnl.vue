<template>
  <div v-loading="loading">
    <!-- 统计卡 -->
    <el-row :gutter="14">
      <el-col :span="6">
        <el-card shadow="hover" class="st-card">
          <div class="st-label">累计收益率</div>
          <div class="st-value num" :class="cls(stats.total_return)">{{ stats.total_return > 0 ? '+' : '' }}{{ stats.total_return }}%</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="st-card">
          <div class="st-label">最大回撤</div>
          <div class="st-value num down">{{ stats.max_drawdown }}%</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="st-card">
          <div class="st-label">盈利天数占比</div>
          <div class="st-value num">{{ stats.win_days_pct }}%</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="st-card">
          <div class="st-label">跟踪天数</div>
          <div class="st-value num">{{ stats.track_days }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 资产 vs 基准 -->
    <el-card shadow="never" style="margin-top: 14px">
      <template #header><div class="panel-title">资产曲线 vs 沪深300基准</div></template>
      <div ref="curveEl" style="height: 300px"></div>
    </el-card>

    <el-row :gutter="14" style="margin-top: 14px">
      <el-col :span="14">
        <el-card shadow="never">
          <template #header><div class="panel-title">每日收益（红盈绿亏）</div></template>
          <div ref="dailyEl" style="height: 260px"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never">
          <template #header><div class="panel-title">月度收益</div></template>
          <el-table :data="months" size="large" max-height="260">
            <el-table-column prop="month" label="月份" width="110" />
            <el-table-column label="月末资产" width="150" align="right">
              <template #default="{ row }"><span class="num">{{ num(row.value) }}</span></template>
            </el-table-column>
            <el-table-column label="月收益" align="right">
              <template #default="{ row }">
                <span class="num" :class="row.ret > 0 ? 'up' : row.ret < 0 ? 'down' : 'flat'">
                  {{ row.ret > 0 ? '+' : '' }}{{ row.ret }}%
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" style="margin-top: 14px">
      <template #header>
        <div class="panel-title">单日极值</div>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="最佳单日">
          <span v-if="stats.best_day" class="num up">{{ stats.best_day.date }}（+{{ stats.best_day.ret }}%）</span>
          <span v-else>—</span>
        </el-descriptions-item>
        <el-descriptions-item label="最差单日">
          <span v-if="stats.worst_day" class="num down">{{ stats.worst_day.date }}（{{ stats.worst_day.ret }}%）</span>
          <span v-else>—</span>
        </el-descriptions-item>
        <el-descriptions-item label="回撤说明">
          以历史峰值计算的最大回落幅度，控制回撤是大赛存活的关键
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import api from '../../api'
import { useUserStore } from '../../stores/user'

const store = useUserStore()
const loading = ref(true)
const curve = ref([])
const benchmark = ref([])
const daily = ref([])
const months = ref([])
const stats = ref({})
const curveEl = ref()
const dailyEl = ref()
let cChart = null
let dChart = null
let timer = null

const contestId = computed(() => store.contest?.id || 0)
window.addEventListener('account-changed', () => load())

function cls(v) {
  return v > 0 ? 'up' : v < 0 ? 'down' : 'flat'
}
function num(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function renderCurve() {
  if (!curveEl.value || !curve.value.length) return
  if (!cChart) cChart = echarts.init(curveEl.value)
  cChart.setOption(
    {
      tooltip: { trigger: 'axis', valueFormatter: (v) => Number(v).toLocaleString() },
      legend: { data: ['我的资产', '沪深300基准'], top: 0, textStyle: { fontSize: 12 } },
      grid: { left: 80, right: 24, top: 30, bottom: 40 },
      xAxis: { type: 'category', data: curve.value.map((p) => p.date), axisLabel: { color: '#8b98ad', fontSize: 11 } },
      yAxis: { type: 'value', scale: true, axisLabel: { color: '#8b98ad', fontSize: 11 }, splitLine: { lineStyle: { color: '#1c1c28' } } },
      dataZoom: [{ type: 'inside' }],
      series: [
        {
          name: '我的资产', type: 'line', data: curve.value.map((p) => p.value), showSymbol: false,
          lineStyle: { width: 2, color: '#8b7cff' },
          areaStyle: { color: 'rgba(124,108,255,0.10)' },
        },
        {
          name: '沪深300基准', type: 'line', data: benchmark.value.map((p) => p.value), showSymbol: false,
          lineStyle: { width: 1.5, color: '#22d3ee', type: 'dashed' },
        },
      ],
    },
    true
  )
}

function renderDaily() {
  if (!dailyEl.value || !daily.value.length) return
  if (!dChart) dChart = echarts.init(dailyEl.value)
  dChart.setOption(
    {
      tooltip: { trigger: 'axis', valueFormatter: (v) => v + '%' },
      grid: { left: 60, right: 20, top: 20, bottom: 34 },
      xAxis: { type: 'category', data: daily.value.map((d) => d.date), axisLabel: { color: '#8b98ad', fontSize: 11 } },
      yAxis: { type: 'value', axisLabel: { color: '#8b98ad', fontSize: 11, formatter: '{value}%' }, splitLine: { lineStyle: { color: '#1c1c28' } } },
      dataZoom: [{ type: 'inside' }],
      series: [{
        type: 'bar',
        data: daily.value.map((d) => ({
          value: d.ret,
          itemStyle: { color: d.ret >= 0 ? '#ff5b66' : '#00c98d' },
        })),
        barMaxWidth: 10,
      }],
    },
    true
  )
}

async function load() {
  const data = await api.get(`/analysis/pnl?contest_id=${contestId.value}`)
  curve.value = data.curve
  benchmark.value = data.benchmark
  daily.value = data.daily
  months.value = data.months
  stats.value = data.stats || {}
  await nextTick()
  renderCurve()
  renderDaily()
}

onMounted(async () => {
  try {
    await load()
    timer = setInterval(load, 20000)
  } finally {
    loading.value = false
  }
})
onBeforeUnmount(() => {
  clearInterval(timer)
  cChart?.dispose()
  dChart?.dispose()
})
</script>

<style scoped>
.st-card { border-radius: 10px; }
.st-label { font-size: 12px; color: var(--text-3); }
.st-value { font-size: 26px; font-weight: 800; margin-top: 6px; color: var(--text-1); }
</style>

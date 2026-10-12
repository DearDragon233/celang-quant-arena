<template>
  <div v-loading="loading">
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card shadow="hover" class="asset-card total">
          <div class="a-label">总资产（元）</div>
          <div class="a-value num">{{ num(acct.total) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="asset-card">
          <div class="a-label">可用资金（元）</div>
          <div class="a-value num">{{ num(acct.cash) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="asset-card">
          <div class="a-label">持仓市值（元）</div>
          <div class="a-value num">{{ num(acct.market_value) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="asset-card">
          <div class="a-label">持仓浮动盈亏（元）</div>
          <div class="a-value num" :class="profitCls">{{ profitSign }}{{ num(profit) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="14">
        <el-card shadow="never">
          <template #header><b>资产走势</b></template>
          <div ref="curveEl" style="height: 300px"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never">
          <template #header>
            <div class="head-row">
              <b>最近成交</b>
              <el-button link type="primary" @click="$router.push('/portal/trade')">去交易</el-button>
            </div>
          </template>
          <el-table :data="orders" size="large" :show-header="false">
            <el-table-column width="60">
              <template #default="{ row }">
                <el-tag :type="row.side === 'buy' ? 'danger' : 'success'" size="small" effect="dark">
                  {{ row.side === 'buy' ? '买' : '卖' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column width="90">
              <template #default="{ row }">{{ row.name }}</template>
            </el-table-column>
            <el-table-column width="150">
              <template #default="{ row }">
                <span class="num">{{ row.price.toFixed(2) }} × {{ row.qty }}</span>
              </template>
            </el-table-column>
            <el-table-column>
              <template #default="{ row }">
                <span class="time">{{ row.time.slice(0, 16) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import api from '../../api'
import { useUserStore } from '../../stores/user'

const userStore = useUserStore()
const contestId = computed(() => userStore.contest?.id || 0)
window.addEventListener('account-changed', () => load())

const acct = ref({ cash: 0, market_value: 0, total: 0, positions: [], curve: [] })
const orders = ref([])
const loading = ref(true)
const curveEl = ref()
let chart = null
let timer = null

const profit = computed(() =>
  acct.value.positions.reduce((s, p) => s + (p.profit || 0), 0)
)
const profitSign = computed(() => (profit.value > 0 ? '+' : ''))
const profitCls = computed(() => (profit.value > 0 ? 'up' : profit.value < 0 ? 'down' : 'flat'))

function num(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function renderCurve() {
  const curve = acct.value.curve || []
  if (!curve.length || !curveEl.value) return
  if (!chart) chart = echarts.init(curveEl.value)
  const values = curve.map((p) => p.value)
  const first = values[0]
  chart.setOption(
    {
      tooltip: { trigger: 'axis', valueFormatter: (v) => Number(v).toLocaleString() },
      grid: { left: 80, right: 24, top: 20, bottom: 34 },
      xAxis: { type: 'category', data: curve.map((p) => p.date), axisLabel: { color: '#606266', fontSize: 11 } },
      yAxis: { type: 'value', scale: true, axisLabel: { color: '#606266', fontSize: 11 }, splitLine: { lineStyle: { color: '#eef1f6' } } },
      dataZoom: [{ type: 'inside' }],
      series: [
        {
          type: 'line',
          data: values,
          showSymbol: false,
          lineStyle: { width: 2, color: values[values.length - 1] >= first ? '#e03131' : '#0ca678' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(124,108,255,0.28)' },
              { offset: 1, color: 'rgba(124,108,255,0.02)' },
            ]),
          },
          markLine: {
            silent: true,
            symbol: 'none',
            label: { formatter: '初始 100 万', fontSize: 11 },
            lineStyle: { color: '#b0b6c0', type: 'dashed' },
            data: [{ yAxis: 1000000 }],
          },
        },
      ],
    },
    true
  )
}

async function load() {
  const [a, o] = await Promise.all([
    api.get(`/trade/account?contest_id=${contestId.value}`),
    api.get(`/trade/orders?size=6&contest_id=${contestId.value}`),
  ])
  acct.value = a
  orders.value = o.items
  await nextTick()
  renderCurve()
}

onMounted(async () => {
  try {
    await load()
    timer = setInterval(load, 10000)
  } finally {
    loading.value = false
  }
})
onBeforeUnmount(() => {
  clearInterval(timer)
  chart?.dispose()
})
</script>

<style scoped>
.asset-card {
  border-radius: 10px;
}

.asset-card.total {
  background: linear-gradient(135deg, #0c0c14, #6d5ef7);
  border: none;
}

.asset-card.total .a-label {
  color: #b9c6dd;
}

.asset-card.total .a-value {
  color: #c4b5fd;
}

.a-label {
  font-size: 13px;
  color: #909399;
}

.a-value {
  font-size: 26px;
  font-weight: 800;
  color: #303133;
  margin-top: 6px;
}

.head-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.time {
  color: #909399;
  font-size: 12px;
}
</style>

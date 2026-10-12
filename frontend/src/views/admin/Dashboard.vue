<template>
  <div v-loading="loading">
    <el-row :gutter="16">
      <el-col v-for="c in cards" :key="c.label" :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat">
            <div class="stat-icon" :style="{ backgroundColor: c.color + '1f', color: c.color }">
              <el-icon :size="26"><component :is="c.icon" /></el-icon>
            </div>
            <div>
              <div class="stat-value num">{{ c.value }}<span v-if="c.prefix" class="suffix">{{ c.prefix }}</span></div>
              <div class="stat-label">{{ c.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>热门交易股票 TOP8（成交笔数）</template>
          <div ref="hotChartEl" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never">
          <template #header>最新成交动态</template>
          <el-table :data="data.latest_orders" size="small" :show-header="false">
            <el-table-column width="120">
              <template #default="{ row }">
                <span class="stu">{{ row.user }}</span>
              </template>
            </el-table-column>
            <el-table-column width="110">
              <template #default="{ row }">
                <span :class="row.side === 'buy' ? 'up' : 'down'">{{ row.side === 'buy' ? '买入' : '卖出' }}</span>
                <span style="margin-left: 6px">{{ row.name }}</span>
              </template>
            </el-table-column>
            <el-table-column label="金额" width="100">
              <template #default="{ row }">{{ Number(row.amount).toLocaleString() }}</template>
            </el-table-column>
            <el-table-column prop="time" width="80">
              <template #default="{ row }">{{ row.time.slice(11) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import api from '../../api'

const loading = ref(true)
const data = ref({ cards: {}, hot_stocks: [], latest_orders: [] })
const hotChartEl = ref()
let chart = null
let timer = null

const cards = computed(() => {
  const c = data.value.cards
  return [
    { label: '注册投资者', value: c.user_count ?? 0, icon: 'User', color: '#7c6cff' },
    { label: '在市股票', value: c.stock_count ?? 0, icon: 'Coin', color: '#22b07d' },
    { label: '总成交笔数', value: c.order_count ?? 0, icon: 'Switch', color: '#e6a23c' },
    { label: '市场总成交额', value: wan(c.turnover), prefix: ' 万', icon: 'Money', color: '#e03131' },
  ]
})

function wan(v) {
  return (Number(v || 0) / 10000).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

function renderChart() {
  const items = (data.value.hot_stocks || []).slice().reverse()
  chart?.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 110, right: 40, top: 10, bottom: 30 },
    xAxis: { type: 'value', minInterval: 1, axisLabel: { color: '#606266' } },
    yAxis: {
      type: 'category',
      data: items.map((i) => `${i.name} ${i.code}`),
      axisLabel: { color: '#303133' },
    },
    series: [
      {
        type: 'bar',
        data: items.map((i) => i.count),
        itemStyle: { color: '#8b7cff', borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', color: '#303133' },
        barMaxWidth: 20,
      },
    ],
  })
}

async function load() {
  data.value = await api.get('/admin/dashboard')
  renderChart()
}

onMounted(async () => {
  try {
    await load()
    chart = echarts.init(hotChartEl.value)
    renderChart()
    window.addEventListener('resize', () => chart?.resize())
    timer = setInterval(load, 8000)
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
.stat-card {
  border-radius: 8px;
}

.stat {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #303133;
}

.suffix {
  font-size: 14px;
  color: #909399;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 2px;
}

.chart {
  height: 300px;
}

.stu {
  font-weight: 600;
}
</style>

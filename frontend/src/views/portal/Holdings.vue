<template>
  <div v-loading="loading">
    <!-- 账户汇总 -->
    <el-row :gutter="14">
      <el-col :span="6">
        <el-card shadow="hover" class="sum-card total">
          <div class="s-label">账户总资产</div>
          <div class="s-value num">{{ num(acct.total) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="sum-card">
          <div class="s-label">累计盈亏</div>
          <div class="s-value num" :class="cls(summary.total_pnl)">{{ sign }}{{ num(summary.total_pnl) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="sum-card">
          <div class="s-label">当日盈亏</div>
          <div class="s-value num" :class="cls(summary.day_pnl)">{{ sign }}{{ num(summary.day_pnl) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="sum-card">
          <div class="s-label">第一大重仓占比</div>
          <div class="s-value num">{{ summary.top1_weight }}%</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="14" style="margin-top: 14px">
      <!-- 持仓占比 -->
      <el-col :span="9">
        <el-card shadow="never">
          <template #header><div class="panel-title">持仓分布（市值占比）</div></template>
          <div ref="pieEl" style="height: 300px"></div>
          <el-empty v-if="!positions.length" description="暂无持仓" :image-size="60" />
        </el-card>
      </el-col>

      <!-- 持仓明细 + 信号 -->
      <el-col :span="15">
        <el-card shadow="never">
          <template #header>
            <div class="panel-title">持仓明细与决策树信号</div>
          </template>
          <el-table :data="positions" size="large" :empty-text="'暂无持仓'">
            <el-table-column label="标的" min-width="130">
              <template #default="{ row }">
                <b>{{ row.name }}</b>
                <span class="sub">{{ row.code }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="qty" label="数量" width="80" align="right" />
            <el-table-column label="占比" width="150">
              <template #default="{ row }">
                <el-progress :percentage="row.weight" :stroke-width="8" :color="'#8b7cff'" :show-text="false" />
                <span class="w-num">{{ row.weight }}%</span>
              </template>
            </el-table-column>
            <el-table-column label="现价" width="95" align="right">
              <template #default="{ row }"><span class="num">{{ row.price.toFixed(2) }}</span></template>
            </el-table-column>
            <el-table-column label="浮盈亏" width="130" align="right">
              <template #default="{ row }">
                <span class="num" :class="cls(row.pnl)">{{ sign }}{{ num(row.pnl) }}（{{ row.pnl_pct > 0 ? '+' : '' }}{{ row.pnl_pct }}%）</span>
              </template>
            </el-table-column>
            <el-table-column label="今日" width="95" align="right">
              <template #default="{ row }">
                <span class="num" :class="cls(row.today_chg)">{{ row.today_chg > 0 ? '+' : '' }}{{ row.today_chg }}%</span>
              </template>
            </el-table-column>
            <el-table-column label="决策树评级" width="120">
              <template #default="{ row }">
                <el-tag :type="verdictType(row.verdict)" effect="dark" size="small">{{ row.verdict }}</el-tag>
                <span class="sub2 num">{{ row.score }}</span>
              </template>
            </el-table-column>
          </el-table>
          <el-alert
            v-if="positions.length"
            type="info"
            :closable="false"
            show-icon
            title="评级来自策略决策树（均线/MACD/RSI 等信号综合评分），强势可做多→继续持有；回避减仓→考虑止盈止损。"
            style="margin-top: 12px"
          />
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

const store = useUserStore()
const loading = ref(true)
const acct = ref({ total: 0, cash: 0, market_value: 0 })
const summary = ref({})
const positions = ref([])
const pieEl = ref()
let pie = null
let timer = null

const contestId = computed(() => store.contest?.id || 0)
window.addEventListener('account-changed', () => load())

const sign = computed(() => {
  const v = summary.value
  const val = v.total_pnl ?? 0
  return val > 0 ? '+' : ''
})

function cls(v) {
  return v > 0 ? 'up' : v < 0 ? 'down' : 'flat'
}
function verdictType(v) {
  return { 强势可做多: 'danger', 回调低吸: 'warning', 持有观察: 'info', 回避减仓: 'success' }[v] || 'info'
}
function num(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function drawPie() {
  if (!positions.value.length || !pieEl.value) return
  if (!pie) pie = echarts.init(pieEl.value)
  pie.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
    legend: { bottom: 0, textStyle: { color: '#b9c4d8', fontSize: 11 } },
    series: [{
      type: 'pie',
      radius: ['42%', '68%'],
      center: ['50%', '44%'],
      label: { show: true, color: '#b9c4d8', formatter: '{b}\n{d}%', fontSize: 11 },
      data: positions.value.map((p, i) => ({
        name: p.name,
        value: p.market_value,
        itemStyle: { color: ['#8b7cff', '#22d3ee', '#ff5b66', '#35c48d', '#e6a23c', '#f56c6c'][i % 6] },
      })),
    }],
  })
}

async function load() {
  const data = await api.get(`/analysis/portfolio?contest_id=${contestId.value}`)
  acct.value = data.account
  summary.value = data.summary
  positions.value = data.positions
  await nextTick()
  drawPie()
}

onMounted(async () => {
  try {
    await load()
    timer = setInterval(load, 15000)
  } finally {
    loading.value = false
  }
})
onBeforeUnmount(() => {
  clearInterval(timer)
  pie?.dispose()
})
</script>

<style scoped>
.sum-card { border-radius: 10px; }
.sum-card.total { background: linear-gradient(135deg, #1b1436, #0f2a3a); border: 1px solid #2c2c40; }
.sum-card.total .s-label { color: #b9a8f0; }
.sum-card.total .s-value { color: #c4b5fd; }

.s-label { font-size: 12px; color: var(--text-3); }
.s-value { font-size: 24px; font-weight: 800; margin-top: 6px; color: var(--text-1); }
.sub { color: var(--text-3); font-size: 11px; margin-left: 6px; }
.sub2 { color: var(--text-3); font-size: 11px; margin-left: 6px; }
.w-num { font-size: 11px; color: var(--text-2); }
</style>

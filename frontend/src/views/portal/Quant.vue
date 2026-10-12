<template>
  <div>
    <el-row :gutter="16">
      <!-- 左：策略配置 -->
      <el-col :span="8">
        <el-card shadow="never">
          <template #header><b>策略配置</b></template>
          <el-form label-width="86px" label-position="left">
            <el-form-item label="策略类型">
              <el-select v-model="form.kind" style="width: 100%" size="large" @change="onKindChange">
                <el-option v-for="k in meta.kinds" :key="k.key" :value="k.key">
                  <span>{{ k.name }}</span>
                  <span class="opt-source">{{ k.source }}</span>
                </el-option>
              </el-select>
              <div class="kind-source" v-if="currentKind.source">来源：{{ currentKind.source }}</div>
            </el-form-item>
            <el-form-item label="标的股票">
              <el-select v-model="form.stock_id" filterable style="width: 100%" size="large" @change="onStockChange">
                <el-option
                  v-for="s in meta.stocks"
                  :key="s.id"
                  :value="s.id"
                  :label="`${s.market === 'CN' ? 'A股' : '美股'} ${s.code} ${s.name}`"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="回测区间">
              <div class="range-row">
                <el-date-picker
                  v-model="form.start_date"
                  type="date"
                  value-format="YYYY-MM-DD"
                  :disabled-date="(d) => disabledDate(d, 'start')"
                  placeholder="开始"
                  style="width: 49%"
                />
                <span>—</span>
                <el-date-picker
                  v-model="form.end_date"
                  type="date"
                  value-format="YYYY-MM-DD"
                  :disabled-date="(d) => disabledDate(d, 'end')"
                  placeholder="结束"
                  style="width: 49%"
                />
              </div>
            </el-form-item>
            <el-form-item label="初始资金">
              <el-input-number
                v-model="form.initial_cash"
                :min="10000"
                :step="10000"
                size="large"
                controls-position="right"
                style="width: 100%"
              />
            </el-form-item>

            <el-divider>{{ kindName }} 参数</el-divider>
            <el-form-item v-for="p in currentKind.params" :key="p" :label="paramLabel(p)">
              <el-input-number
                v-model="form.params[p]"
                :min="p === 'fast' || p === 'slow' || p === 'period' || p === 'signal' ? 2 : 1"
                :max="p === 'k' ? 5 : 120"
                :step="p === 'k' ? 0.5 : 1"
                size="large"
                controls-position="right"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="策略名称">
              <el-input v-model="form.name" maxlength="50" placeholder="便于识别的名称" />
            </el-form-item>

            <el-button
              type="primary"
              size="large"
              class="run-btn"
              :loading="running"
              :disabled="!form.stock_id"
              @click="run"
            >
              {{ running ? '回测运行中…' : '▶ 运行回测' }}
            </el-button>
            <el-button size="large" :disabled="!result || saving" @click="saveRun">保存本次结果</el-button>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右：回测结果 -->
      <el-col :span="16">
        <el-card shadow="never" v-loading="running" element-loading-text="正在逐日撮合回测…">
          <template #header>
            <div class="res-head">
              <b>回测报告</b>
              <span v-if="result" class="res-meta">
                {{ resultTitle }}
              </span>
            </div>
          </template>

          <template v-if="result">
            <el-row :gutter="12">
              <el-col :span="6">
                <div class="metric-card" :class="metricCls(result.metrics.total_return)">
                  <div class="m-value num">{{ result.metrics.total_return }}%</div>
                  <div class="m-label">总收益率</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="metric-card">
                  <div class="m-value num">{{ result.metrics.annual_return }}%</div>
                  <div class="m-label">年化收益</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="metric-card danger-zone">
                  <div class="m-value num">{{ result.metrics.max_drawdown }}%</div>
                  <div class="m-label">最大回撤</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="metric-card gold-zone">
                  <div class="m-value num">{{ result.metrics.sharpe }}</div>
                  <div class="m-label">夏普比率</div>
                </div>
              </el-col>
            </el-row>
            <div class="sub-metrics">
              <span>基准收益（买入持有）<b class="num">{{ result.metrics.benchmark_return }}%</b></span>
              <span>交易次数 <b class="num">{{ result.metrics.trade_count }}</b></span>
              <span>胜率 <b class="num">{{ result.metrics.win_rate }}%</b></span>
              <span>平均每次收益 <b class="num">{{ result.metrics.avg_hold_ret }}%</b></span>
              <span>期末资产 <b class="num">{{ num(result.metrics.final_value) }}</b></span>
            </div>

            <div class="chart-title">
              策略净值 vs 基准（▲ 买入口径在K线上标注）
              <el-radio-group v-model="resultRange" size="small" style="margin-left: auto" @change="rerunRange">
                <el-radio-button value="all">全部</el-radio-button>
                <el-radio-button value="half">近半程</el-radio-button>
              </el-radio-group>
            </div>
            <div ref="equityEl" style="height: 300px"></div>

            <div class="chart-title" style="margin-top: 8px">标的K线与买卖点</div>
            <KLineChart :bars="resultBars" :trades="result.trades" :height="320" />
          </template>
          <el-empty v-else description="配置策略后点击「运行回测」查看报告" :image-size="90" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header><b>我的策略</b></template>
          <el-table :data="strategies" size="large" :empty-text="'还没有保存的策略'">
            <el-table-column prop="name" label="名称" min-width="130" show-overflow-tooltip />
            <el-table-column label="标的" width="120">
              <template #default="{ row }">{{ row.stock_name }}</template>
            </el-table-column>
            <el-table-column prop="kind_name" label="类型" width="120" />
            <el-table-column label="区间" width="180">
              <template #default="{ row }">
                <span class="num">{{ row.start_date }} ~ {{ row.end_date.slice(5) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="loadStrategy(row)">载入</el-button>
                <el-button link type="danger" @click="delStrategy(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header><b>回测历史（最近 30 次）</b></template>
          <el-table
            :data="runs"
            size="large"
            :empty-text="'保存回测后会出现在这里'"
            highlight-current-row
            @row-click="viewRun"
            style="cursor: pointer"
          >
            <el-table-column prop="strategy_name" label="名称" min-width="120" show-overflow-tooltip />
            <el-table-column prop="kind_name" label="类型" width="110" />
            <el-table-column label="总收益" width="90" align="right">
              <template #default="{ row }">
                <span class="num" :class="metricCls(row.metrics.total_return)">
                  {{ row.metrics.total_return }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="夏普" width="70" align="right">
              <template #default="{ row }">{{ row.metrics.sharpe }}</template>
            </el-table-column>
            <el-table-column label="回撤" width="80" align="right">
              <template #default="{ row }">{{ row.metrics.max_drawdown }}%</template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="110">
              <template #default="{ row }">{{ row.created_at.slice(5, 16) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import api from '../../api'
import KLineChart from '../../components/KLineChart.vue'

const PARAM_NAMES = {
  fast: '快线周期', slow: '慢线周期', signal: '信号周期',
  period: '周期', oversold: '超卖阈值', overbought: '超买阈值', k: '带宽倍数',
}

const meta = ref({ kinds: [], stocks: [] })
const strategies = ref([])
const runs = ref([])
const form = reactive({
  kind: 'dual_ma', stock_id: null, start_date: '', end_date: '',
  initial_cash: 100000, params: { fast: 5, slow: 20 }, name: '',
})
const running = ref(false)
const saving = ref(false)
const result = ref(null)
const resultBars = ref([])
const resultRange = ref('all')
const equityEl = ref()
let equityChart = null

const currentKind = computed(
  () => meta.value.kinds.find((k) => k.key === form.kind) || { params: [], defaults: {} }
)
const kindName = computed(() => currentKind.value.name || '')
const stockMeta = computed(() => meta.value.stocks.find((s) => s.id === form.stock_id))
const resultTitle = computed(() => {
  if (!result.value) return ''
  const s = meta.value.stocks.find((x) => x.id === form.stock_id)
  return s ? `${s.code} ${s.name} · ${form.start_date} ~ ${form.end_date}` : ''
})

function num(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function metricCls(v) {
  return v > 0 ? 'up' : v < 0 ? 'down' : 'flat'
}
function paramLabel(p) {
  return PARAM_NAMES[p] || p
}

function disabledDate(d, which) {
  if (!stockMeta.value || !stockMeta.value.start) return false
  const s = stockMeta.value.start, e = stockMeta.value.end
  const t = d.getTime()
  const lo = new Date(s + 'T00:00:00').getTime()
  const hi = new Date(e + 'T00:00:00').getTime()
  return which === 'start' ? t < lo || t > hi : t < lo || t > hi
}

function onKindChange() {
  form.params = { ...currentKind.value.defaults }
}

function onStockChange() {
  if (stockMeta.value) {
    const s = stockMeta.value
    const st = new Date(s.start)
    st.setMonth(st.getMonth() + 6)
    form.start_date = s.start
    form.end_date = s.end
  }
}

async function loadLists() {
  ;[strategies.value, runs.value] = await Promise.all([api.get('/quant/strategies'), api.get('/quant/runs')])
}

async function run() {
  if (!form.name) form.name = `${kindName.value}·${new Date().toLocaleDateString('zh-CN')}`
  running.value = true
  try {
    const data = await api.post('/quant/backtest', { ...form })
    result.value = data
    resultBars.value = data.bars
    resultRange.value = 'all'
    await nextTick()
    renderEquity(data.equity)
  } finally {
    running.value = false
  }
}

function rerunRange() {
  if (!result.value) return
  const eq = result.value.equity
  const data = resultRange.value === 'half' ? eq.slice(Math.floor(eq.length / 2)) : eq
  renderEquity(data)
}

function renderEquity(equity) {
  if (!equityChart) equityChart = echarts.init(equityEl.value)
  const dates = equity.map((p) => p.date)
  const base = equity[0]?.value || 1
  equityChart.setOption(
    {
      animation: false,
      tooltip: { trigger: 'axis', valueFormatter: (v) => Number(v).toLocaleString() },
      legend: { data: ['策略净值', '买入持有基准'], top: 0, textStyle: { fontSize: 12 } },
      grid: { left: 70, right: 30, top: 30, bottom: 40 },
      xAxis: { type: 'category', data: dates, axisLabel: { color: '#606266', fontSize: 11 } },
      yAxis: { type: 'value', scale: true, axisLabel: { color: '#606266', fontSize: 11 }, splitLine: { lineStyle: { color: '#eef1f6' } } },
      dataZoom: [{ type: 'inside' }],
      series: [
        {
          name: '策略净值', type: 'line', data: equity.map((p) => p.value), showSymbol: false,
          lineStyle: { width: 2, color: '#8b7cff' },
          areaStyle: { color: 'rgba(124,108,255,0.10)' },
        },
        {
          name: '买入持有基准', type: 'line', data: equity.map((p) => p.benchmark), showSymbol: false,
          lineStyle: { width: 1.5, color: '#7a8ba6', type: 'dashed' },
        },
      ],
    },
    true
  )
}

async function saveRun() {
  saving.value = true
  try {
    await api.post('/quant/backtest/save', { ...form })
    ElMessage.success('已保存到回测历史')
    loadLists()
  } finally {
    saving.value = false
  }
}

function loadStrategy(row) {
  form.name = row.name
  form.kind = row.kind
  form.stock_id = row.stock_id
  form.params = { ...row.params }
  form.start_date = row.start_date
  form.end_date = row.end_date
  form.initial_cash = row.initial_cash
  onKindChange()
  form.params = { ...row.params }
  ElMessage.success(`已载入策略「${row.name}」，点击运行回测`)
}

async function delStrategy(row) {
  await ElMessageBox.confirm(`删除策略「${row.name}」？`, '删除确认', { type: 'warning' })
  await api.delete(`/quant/strategies/${row.id}`)
  ElMessage.success('已删除')
  loadLists()
}

async function viewRun(row) {
  const d = await api.get(`/quant/runs/${row.id}`)
  form.name = d.strategy_name
  form.kind = d.kind
  form.stock_id = meta.value.stocks.find((s) => s.code === d.code)?.id || null
  form.params = { ...d.params }
  form.start_date = d.start_date
  form.end_date = d.end_date
  form.initial_cash = d.initial_cash
  result.value = { metrics: d.metrics, equity: d.equity, trades: d.trades }
  resultBars.value = []
  await nextTick()
  renderEquity(d.equity)
  ElMessage.success('已载入历史回测报告')
}

onMounted(async () => {
  meta.value = await api.get('/quant/meta')
  form.params = { ...(meta.value.kinds[0]?.defaults || {}) }
  if (meta.value.stocks.length) {
    form.stock_id = meta.value.stocks[0].id
    onStockChange()
  }
  loadLists()
})
</script>

<style scoped>
.kind-source { font-size: 12px; color: #8a94a8; margin-top: 4px; }
.opt-source { float: right; font-size: 11px; color: #5d6b85; margin-left: 12px; }

.range-row {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
}

.run-btn {
  width: 60%;
  font-weight: 700;
  letter-spacing: 2px;
}

.res-head {
  display: flex;
  align-items: center;
  gap: 14px;
}

.res-meta {
  font-size: 13px;
  color: #909399;
}

.metric-card {
  border-radius: 10px;
  background: #f6f8fb;
  text-align: center;
  padding: 14px 0;
}

.metric-card .m-value {
  font-size: 24px;
  font-weight: 800;
  color: #303133;
}

.metric-card.danger-zone .m-value {
  color: #e03131;
}

.metric-card.gold-zone .m-value {
  color: #6d5ef7;
}

.m-label {
  font-size: 12px;
  color: #909399;
  margin-top: 3px;
}

.sub-metrics {
  display: flex;
  gap: 22px;
  flex-wrap: wrap;
  margin: 12px 0 4px;
  font-size: 13px;
  color: #5a6070;
}

.sub-metrics b {
  color: #303133;
}

.chart-title {
  display: flex;
  align-items: center;
  font-size: 13px;
  color: #5a6070;
  margin: 10px 0 4px;
  font-weight: 600;
}
</style>

<template>
  <div v-loading="loading">
    <el-row :gutter="16">
      <!-- 左：行情与K线 -->
      <el-col :span="17">
        <el-card shadow="never" body-style="padding: 14px 18px">
          <div class="stock-picker">
            <el-select
              v-model="currentId"
              filterable
              placeholder="选择股票"
              style="width: 240px"
              size="large"
              @change="loadAll"
            >
              <el-option v-for="s in stocks" :key="s.id" :value="s.id" :label="`${s.code} ${s.name}`" />
            </el-select>
            <template v-if="quote">
              <span class="q-name">{{ quote.name }}</span>
              <el-tag size="small" :type="quote.market === 'CN' ? 'info' : 'warning'" effect="dark">
                {{ quote.market === 'CN' ? 'A股' : '美股' }}
              </el-tag>
              <span class="q-price num" :class="cls(quote.change_pct)">{{ quote.price.toFixed(2) }}</span>
              <el-tag :type="tagType(quote.change_pct)" effect="dark" size="small" class="num">
                {{ quote.change_pct > 0 ? '+' : '' }}{{ quote.change_pct }}%
              </el-tag>
              <span class="q-meta">今开 {{ quote.open?.toFixed(2) }}　最高
                <span class="up">{{ quote.high?.toFixed(2) }}</span>　最低
                <span class="down">{{ quote.low?.toFixed(2) }}</span>
              </span>
            </template>
          </div>
          <KLineChart :bars="bars" :height="400" />
        </el-card>

        <el-card shadow="never" style="margin-top: 16px">
          <template #header>
            <div class="sec-head">
              <span>我的持仓</span>
              <el-button link type="primary" @click="loadAll">刷新</el-button>
            </div>
          </template>
          <el-table :data="positions" size="large" :empty-text="'暂无持仓，去下单吧'">
            <el-table-column prop="code" label="代码" width="90" />
            <el-table-column prop="name" label="名称" width="110" />
            <el-table-column prop="qty" label="持仓数量" width="100" align="right" />
            <el-table-column label="成本价" width="100" align="right">
              <template #default="{ row }">{{ row.avg_cost.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="现价" width="100" align="right">
              <template #default="{ row }">
                <span :class="cls(row.profit_pct)">{{ row.price.toFixed(2) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="市值" width="120" align="right">
              <template #default="{ row }">{{ num(row.market_value) }}</template>
            </el-table-column>
            <el-table-column label="浮动盈亏" align="right">
              <template #default="{ row }">
                <span class="num" :class="cls(row.profit)">
                  {{ row.profit > 0 ? '+' : '' }}{{ num(row.profit) }}（{{ row.profit_pct > 0 ? '+' : '' }}{{ row.profit_pct }}%）
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button link type="success" @click="quickSell(row)">卖出</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 右：交易面板 -->
      <el-col :span="7">
        <el-card shadow="never" class="trade-panel">
          <template #header>
            <div class="panel-head">
              <span>模拟下单 · {{ contestName }}</span>
              <span class="cash num">可用 {{ num(cash) }}</span>
            </div>
          </template>
          <el-tabs v-model="side" stretch>
            <el-tab-pane label="买入" name="buy">
              <div class="form-row">
                <span class="form-label">买入价格</span>
                <el-input :model-value="quote?.price?.toFixed(2) || '--'" disabled size="large">
                  <template #append>元/股（市价）</template>
                </el-input>
              </div>
              <div class="form-row">
                <span class="form-label">买入数量</span>
                <el-input-number
                  v-model="qty"
                  :min="100"
                  :step="100"
                  :max="1000000"
                  size="large"
                  controls-position="right"
                  style="width: 100%"
                />
              </div>
              <div class="quick-row">
                <el-button v-for="q in quickQtys" :key="q" size="small" plain @click="qty = q">
                  {{ q }}股
                </el-button>
                <el-button size="small" plain type="warning" @click="maxBuy">全仓</el-button>
              </div>
              <div class="calc-row">
                <span>预计金额</span><b class="num">{{ num(estAmount) }}</b>
              </div>
              <div class="calc-row">
                <span>预计费用（万3，最低5元）</span><b class="num">{{ estFee.toFixed(2) }}</b>
              </div>
              <el-button
                type="danger"
                size="large"
                class="submit-btn"
                :loading="submitting"
                :disabled="!quote"
                @click="submit('buy')"
              >
                买 入
              </el-button>
            </el-tab-pane>

            <el-tab-pane label="卖出" name="sell">
              <div class="form-row">
                <span class="form-label">卖出价格</span>
                <el-input :model-value="quote?.price?.toFixed(2) || '--'" disabled size="large">
                  <template #append>元/股（市价）</template>
                </el-input>
              </div>
              <div class="form-row">
                <span class="form-label">卖出数量</span>
                <el-input-number
                  v-model="qty"
                  :min="100"
                  :step="100"
                  size="large"
                  controls-position="right"
                  style="width: 100%"
                />
              </div>
              <div class="quick-row">
                <el-button size="small" plain type="warning" @click="maxSell">清仓</el-button>
                <span class="hold-tip" v-if="holdQty">当前持有 {{ holdQty }} 股</span>
              </div>
              <div class="calc-row">
                <span>预计到账</span><b class="num">{{ num(estAmount - estFeeSell) }}</b>
              </div>
              <div class="calc-row">
                <span>费用（含印花税 0.05%）</span><b class="num">{{ estFeeSell.toFixed(2) }}</b>
              </div>
              <el-button
                type="success"
                size="large"
                class="submit-btn"
                :loading="submitting"
                :disabled="!holdQty"
                @click="submit('sell')"
              >
                卖 出
              </el-button>
            </el-tab-pane>
          </el-tabs>

          <el-divider>最近成交</el-divider>
          <div class="recent">
            <div v-for="o in recentOrders" :key="o.id" class="recent-item">
              <span :class="o.side === 'buy' ? 'up' : 'down'">{{ o.side === 'buy' ? '买' : '卖' }}</span>
              <span>{{ o.name }}</span>
              <span class="num">{{ Number(o.price).toFixed(2) }} × {{ o.qty }}</span>
            </div>
            <el-empty v-if="!recentOrders.length" description="暂无成交" :image-size="50" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'
import { useUserStore } from '../../stores/user'
import KLineChart from '../../components/KLineChart.vue'

const userStore = useUserStore()
const contestId = computed(() => userStore.contest?.id || 0)
const contestName = computed(() => userStore.contest?.name || '年度场（常驻）')
window.addEventListener('account-changed', () => loadAll())

const FEE_RATE = 0.0003
const MIN_FEE = 5
const STAMP = 0.0005

const stocks = ref([])
const currentId = ref(null)
const quote = ref(null)
const bars = ref([])
const positions = ref([])
const cash = ref(0)
const recentOrders = ref([])
const qty = ref(100)
const side = ref('buy')
const loading = ref(true)
const submitting = ref(false)
const route = useRoute()

const lot = computed(() => (quote.value?.market === 'US' ? 1 : 100))

function num(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function cls(v) {
  return v > 0 ? 'up' : v < 0 ? 'down' : 'flat'
}
function tagType(v) {
  return v > 0 ? 'danger' : v < 0 ? 'success' : 'info'
}

const holdQty = computed(() => {
  const p = positions.value.find((x) => x.stock_id === currentId.value)
  return p ? p.qty : 0
})

const quickQtys = computed(() =>
  quote.value?.market === 'US' ? [1, 10, 50, 100] : [100, 300, 500, 1000]
)

const estAmount = computed(() => (quote.value ? quote.value.price * qty.value : 0))
const estFee = computed(() => Math.max(estAmount.value * FEE_RATE, MIN_FEE))
const estFeeSell = computed(() => Math.max(estAmount.value * (FEE_RATE + STAMP), MIN_FEE))

async function loadAll() {
  const [stockList, acct, orders] = await Promise.all([
    api.get('/market/stocks'),
    api.get(`/trade/account?contest_id=${contestId.value}`),
    api.get(`/trade/orders?size=5&contest_id=${contestId.value}`),
  ])
  stocks.value = stockList
  positions.value = acct.positions
  cash.value = acct.cash
  recentOrders.value = orders.items
  if (!currentId.value && stockList.length) currentId.value = stockList[0].id
  quote.value = stockList.find((s) => s.id === currentId.value) || null
  if (currentId.value) {
    const data = await api.get(`/market/kline/${currentId.value}?days=120`)
    bars.value = data.bars
  }
}

function maxBuy() {
  if (!quote.value) return
  qty.value = Math.max(Math.floor(cash.value / (quote.value.price * (1 + FEE_RATE)) / lot.value) * lot.value, 0)
}
function maxSell() {
  qty.value = Math.max(holdQty.value, 0)
}
function quickSell(row) {
  currentId.value = row.stock_id
  side.value = 'sell'
  quote.value = stocks.value.find((s) => s.id === row.stock_id) || quote.value
  loadKlineOnly()
  qty.value = row.qty
}

async function loadKlineOnly() {
  if (!currentId.value) return
  const data = await api.get(`/market/kline/${currentId.value}?days=120`)
  bars.value = data.bars
}

async function submit(action) {
  const text = action === 'buy'
    ? `以市价 ${quote.value.price.toFixed(2)} 元买入 ${qty.value} 股 ${quote.value.name}？预计花费 ${num(estAmount.value + estFee.value)} 元。`
    : `以市价 ${quote.value.price.toFixed(2)} 元卖出 ${qty.value} 股？预计到账 ${num(estAmount.value - estFeeSell.value)} 元。`
  await ElMessageBox.confirm(text, action === 'buy' ? '买入确认' : '卖出确认', { type: 'warning' })
  submitting.value = true
  try {
    const r = await api.post(`/trade/${action}`, {
      stock_id: currentId.value, qty: qty.value, contest_id: contestId.value,
    })
    ElMessage.success(`${action === 'buy' ? '买入' : '卖出'}成功：${r.date} @ ${r.price}`)
    await loadAll()
    window.dispatchEvent(new CustomEvent('equity-refresh'))
  } finally {
    submitting.value = false
  }
}

let pollTimer = null

onMounted(async () => {
  try {
    await loadAll()
    // 支持从策略决策树「去执行」带入标的
    const qid = Number(route.query.stock_id)
    if (qid && stocks.value.some((s) => s.id === qid)) {
      currentId.value = qid
      quote.value = stocks.value.find((s) => s.id === qid)
      await loadKlineOnly()
    }
    pollTimer = setInterval(() => loadAll(), 15000)
  } finally {
    loading.value = false
  }
})
onBeforeUnmount(() => clearInterval(pollTimer))
</script>

<style scoped>
.stock-picker {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.q-name {
  font-size: 18px;
  font-weight: 700;
}

.q-price {
  font-size: 26px;
  font-weight: 800;
}

.q-meta {
  color: #909399;
  font-size: 13px;
}

.sec-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.cash {
  font-size: 13px;
  color: #6d5ef7;
}

.form-row {
  margin-bottom: 14px;
}

.form-label {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.quick-row {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
  align-items: center;
}

.hold-tip {
  font-size: 12px;
  color: #909399;
}

.calc-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #5a6070;
  padding: 5px 0;
}

.calc-row b {
  color: #303133;
}

.submit-btn {
  width: 100%;
  margin-top: 12px;
  font-weight: 700;
  letter-spacing: 6px;
  font-size: 16px;
}

.recent {
  max-height: 200px;
  overflow: auto;
}

.recent-item {
  display: flex;
  gap: 10px;
  font-size: 13px;
  padding: 6px 0;
  border-bottom: 1px dashed #f0f2f5;
  color: #5a6070;
}
</style>

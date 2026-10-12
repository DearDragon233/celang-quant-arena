<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="head">
          <span>行情中心</span>
          <div style="display:flex;align-items:center;gap:12px">
            <span class="mkt-tip">真实行情（A股 + 美股） · 红涨绿跌</span>
            <el-switch v-model="autoRefresh" active-text="实时刷新" size="small" />
          </div>
        </div>
      </template>

      <el-table
        :data="stocks"
        v-loading="loading"
        highlight-current-row
        @row-click="onPick"
        style="width: 100%"
        size="large"
      >
        <el-table-column prop="code" label="代码" width="90" />
        <el-table-column prop="name" label="名称" width="110">
          <template #default="{ row }"><b>{{ row.name }}</b></template>
        </el-table-column>
        <el-table-column prop="sector" label="板块" width="100" />
        <el-table-column label="市场" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.market === 'CN' ? 'info' : 'warning'" effect="plain">
              {{ row.market === 'CN' ? 'A股' : '美股' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最新价" width="110" align="right">
          <template #default="{ row }">
            <span class="num" :class="cls(row.change_pct)">{{ row.price.toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="涨跌幅" width="110" align="right">
          <template #default="{ row }">
            <el-tag :type="tagType(row.change_pct)" effect="dark" size="small" class="num" style="width: 76px">
              {{ row.change_pct > 0 ? '+' : '' }}{{ row.change_pct }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="今开" width="100" align="right">
          <template #default="{ row }">{{ fmt2(row.open) }}</template>
        </el-table-column>
        <el-table-column label="最高" width="100" align="right">
          <template #default="{ row }">
            <span class="num up">{{ fmt2(row.high) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="最低" width="100" align="right">
          <template #default="{ row }">
            <span class="num down">{{ fmt2(row.low) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="昨收" width="100" align="right">
          <template #default="{ row }">{{ fmt2(row.prev_close) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-drawer v-model="drawerVisible" :title="detailTitle" size="72%" destroy-on-close>
      <div v-loading="kloading">
        <div class="quote-head" v-if="quote">
          <div class="q-item">
            <span class="q-label">最新价</span>
            <span class="q-value num" :class="cls(quote.change_pct)">{{ quote.price.toFixed(2) }}</span>
          </div>
          <div class="q-item">
            <span class="q-label">涨跌幅</span>
            <span class="q-value num" :class="cls(quote.change_pct)">
              {{ quote.change_pct > 0 ? '+' : '' }}{{ quote.change_pct }}%
            </span>
          </div>
          <div class="q-item"><span class="q-label">今开</span><span class="num">{{ fmt2(quote.open) }}</span></div>
          <div class="q-item"><span class="q-label">最高</span><span class="num up">{{ fmt2(quote.high) }}</span></div>
          <div class="q-item"><span class="q-label">最低</span><span class="num down">{{ fmt2(quote.low) }}</span></div>
          <div class="q-item"><span class="q-label">昨收</span><span class="num">{{ fmt2(quote.prev_close) }}</span></div>
          <el-radio-group v-model="rangeDays" size="small" @change="loadKline">
            <el-radio-button :value="60">60日</el-radio-button>
            <el-radio-button :value="120">120日</el-radio-button>
            <el-radio-button :value="250">一年</el-radio-button>
          </el-radio-group>
        </div>
        <KLineChart :bars="bars" :height="430" />
        <div class="stock-desc" v-if="desc">{{ desc }}</div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import api from '../../api'
import KLineChart from '../../components/KLineChart.vue'

const stocks = ref([])
const loading = ref(true)
const drawerVisible = ref(false)
const kloading = ref(false)
const current = ref(null)
const quote = ref(null)
const bars = ref([])
const rangeDays = ref(120)

const detailTitle = computed(() =>
  current.value ? `${current.value.name}（${current.value.code}）` : ''
)
const desc = computed(() => current.value?.description || '')

function cls(v) {
  return v > 0 ? 'up' : v < 0 ? 'down' : 'flat'
}
function fmt2(v) {
  return v == null || isNaN(v) ? '--' : Number(v).toFixed(2)
}
function tagType(v) {
  return v > 0 ? 'danger' : v < 0 ? 'success' : 'info'
}

async function load() {
  loading.value = true
  try {
    stocks.value = await api.get('/market/stocks')
  } finally {
    loading.value = false
  }
}

async function onPick(row) {
  current.value = row
  quote.value = row
  drawerVisible.value = true
  await loadKline()
}

async function loadKline() {
  kloading.value = true
  try {
    const data = await api.get(`/market/kline/${current.value.id}?days=${rangeDays.value}`)
    bars.value = data.bars
  } finally {
    kloading.value = false
  }
}

const autoRefresh = ref(true)
let timer = null

onMounted(() => {
  load()
  timer = setInterval(() => {
    if (autoRefresh.value) load()
  }, 10000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.mkt-tip {
  font-size: 12px;
  color: #b0b6c0;
  font-weight: 400;
}

.quote-head {
  display: flex;
  align-items: center;
  gap: 26px;
  padding: 4px 0 14px;
  flex-wrap: wrap;
}

.q-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.q-label {
  font-size: 11px;
  color: #909399;
}

.q-value {
  font-size: 20px;
  font-weight: 700;
}

.stock-desc {
  margin-top: 10px;
  color: #909399;
  font-size: 13px;
}

:deep(.el-table__row) {
  cursor: pointer;
}
</style>

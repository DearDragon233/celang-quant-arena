<template>
  <div v-loading="loading">
    <!-- 竞技场横幅 -->
    <div class="arena-banner">
      <div class="ab-left">
        <span class="ab-icon">⚔️</span>
        <div>
          <div class="ab-title">NPC 竞技场 · 赛博斗蛐蛐</div>
          <div class="ab-sub">8 位风格迥异的传奇交易者，在真实行情上自动对战 · 每个交易日收盘后自动更新战绩</div>
        </div>
      </div>
      <div class="ab-me" v-if="me">
        <div class="ab-me-label">我的成绩</div>
        <div class="ab-me-value num" :class="me.return_pct > 0 ? 'up' : 'down'">
          {{ me.return_pct > 0 ? '+' : '' }}{{ me.return_pct }}%
        </div>
        <div class="ab-me-note">{{ me.beats_best_npc ? '🏆 目前跑赢全部 NPC，守住！' : '被最强 NPC 压制中，去决策树找灵感' }}</div>
      </div>
    </div>

    <!-- NPC 卡片 -->
    <div class="npc-grid">
      <div v-for="n in npcs" :key="n.id" class="npc-card" :class="'rank-' + n.rank" @click="openDetail(n)">
        <div class="nc-top">
          <span class="nc-avatar">{{ n.avatar }}</span>
          <div class="nc-id">
            <div class="nc-name">
              <span class="rank-badge" :class="'r' + n.rank">{{ n.rank }}</span>
              {{ n.name }}
              <span class="nc-title">{{ n.title }}</span>
            </div>
            <div class="nc-style">{{ n.style_tag }} · 做 {{ n.stock }}</div>
          </div>
          <div class="nc-return num" :class="n.return_pct > 0 ? 'up' : 'down'">
            {{ n.return_pct > 0 ? '+' : '' }}{{ n.return_pct }}%
          </div>
        </div>
        <div class="nc-stats">
          <span>总资产 <b class="num">{{ num(n.total) }}</b></span>
          <span>持仓 <b class="num">{{ n.holding }}</b> 股</span>
          <span>操作 <b class="num">{{ n.order_count }}</b> 次</span>
        </div>
        <div class="nc-curve" :cid="n.id"></div>
        <div class="nc-action" v-if="n.last_action">
          <el-tag :type="n.last_action.side === 'buy' ? 'danger' : 'success'" size="small" effect="dark">
            {{ n.last_action.side === 'buy' ? '买' : '卖' }}
          </el-tag>
          <span class="nc-action-text">{{ n.last_action.text }}</span>
          <span class="nc-action-date">{{ n.last_action.date }}</span>
        </div>
      </div>
    </div>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" :title="detailTitle" size="62%" destroy-on-close>
      <div v-loading="detailLoading">
        <div class="dt-bio" v-if="detail.trader">
          <span class="dt-avatar">{{ detail.trader.avatar }}</span>
          <div>
            <b>{{ detail.trader.name }}</b>
            <span class="sub">{{ detail.trader.title }} · {{ detail.trader.style_tag }}</span>
            <p class="dt-quote">“{{ detail.trader.bio }}”</p>
          </div>
        </div>
        <div class="dt-sec">净值曲线</div>
        <div ref="curveEl" style="height: 260px"></div>
        <div class="dt-sec">操作流水（含决策理由）</div>
        <el-table :data="detail.orders" size="large">
          <el-table-column prop="date" label="日期" width="110" />
          <el-table-column label="方向" width="70">
            <template #default="{ row }">
              <el-tag :type="row.side === 'buy' ? 'danger' : 'success'" size="small" effect="dark">
                {{ row.side === 'buy' ? '买入' : '卖出' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="价格" width="100" align="right">
            <template #default="{ row }"><span class="num">{{ row.price.toFixed(2) }}</span></template>
          </el-table-column>
          <el-table-column label="数量" width="90" align="right" prop="qty" />
          <el-table-column prop="reason" label="决策理由" min-width="220" show-overflow-tooltip />
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import api from '../../api'

const loading = ref(true)
const npcs = ref([])
const me = ref(null)
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref({ trader: null, orders: [], curve: [] })
const detailTitle = ref('')
const curveEl = ref()
let chart = null
let timer = null
const miniCharts = []

function num(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function drawMinis() {
  for (const n of npcs.value) {
    const el = document.querySelector(`.nc-curve[cid='${n.id}']`)
    if (!el) continue
    let c = miniCharts.find((m) => m.id === n.id)
    if (!c) {
      c = { id: n.id, chart: echarts.init(el) }
      miniCharts.push(c)
    }
    const values = n.curve.map((p) => p.value)
    const last = values[values.length - 1] || 1
    const color = last >= (n.curve[0]?.value || 1) ? '#ff5b5b' : '#35c48d'
    c.chart.setOption({
      grid: { left: 0, right: 0, top: 4, bottom: 0 },
      xAxis: { type: 'category', data: n.curve.map((p) => p.date), show: false },
      yAxis: { type: 'value', show: false, scale: true },
      series: [{ type: 'line', data: values, showSymbol: false, lineStyle: { width: 1.5, color } }],
    })
  }
}

async function load() {
  const data = await api.get('/npc/arena')
  npcs.value = data.npcs
  me.value = data.me
  await nextTick()
  drawMinis()
}

async function openDetail(n) {
  detailVisible.value = true
  detailLoading.value = true
  detailTitle.value = `${n.avatar} ${n.name} · ${n.title}`
  try {
    detail.value = await api.get(`/npc/${n.id}`)
    await nextTick()
    if (curveEl.value) {
      chart?.dispose()
      chart = echarts.init(curveEl.value)
      const curve = detail.value.curve
      const values = curve.map((p) => p.value)
      chart.setOption({
        tooltip: { trigger: 'axis', valueFormatter: (v) => Number(v).toLocaleString() },
        grid: { left: 80, right: 20, top: 16, bottom: 30 },
        xAxis: { type: 'category', data: curve.map((p) => p.date), axisLabel: { color: '#8b98ad', fontSize: 11 } },
        yAxis: { type: 'value', scale: true, axisLabel: { color: '#8b98ad', fontSize: 11 }, splitLine: { lineStyle: { color: '#1a2540' } } },
        dataZoom: [{ type: 'inside' }],
        series: [{
          type: 'line', data: values, showSymbol: false,
          lineStyle: { width: 2, color: values[values.length - 1] >= values[0] ? '#ff5b5b' : '#35c48d' },
          areaStyle: { color: 'rgba(124,108,255,0.08)' },
        }],
      })
    }
  } finally {
    detailLoading.value = false
  }
}

onMounted(async () => {
  try {
    await load()
    timer = setInterval(load, 30000)
  } finally {
    loading.value = false
  }
})
onBeforeUnmount(() => {
  clearInterval(timer)
  miniCharts.forEach((m) => m.chart.dispose())
  chart?.dispose()
})
</script>

<style scoped>
.arena-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background:
    radial-gradient(500px 200px at 15% 0%, rgba(255, 91, 91, 0.12), transparent),
    radial-gradient(500px 200px at 85% 100%, rgba(124, 108, 255, 0.1), transparent),
    linear-gradient(120deg, #17203a, #0e1626);
  border: 1px solid #2c2c40;
  border-radius: 12px;
  padding: 18px 24px;
  margin-bottom: 16px;
}

.ab-left { display: flex; align-items: center; gap: 16px; }
.ab-icon { font-size: 34px; }
.ab-title { font-size: 20px; font-weight: 800; color: #fff; letter-spacing: 1px; }
.ab-sub { font-size: 12px; color: var(--text-2); margin-top: 4px; }

.ab-me { text-align: center; background: rgba(255, 255, 255, 0.04); border-radius: 10px; padding: 8px 22px; }
.ab-me-label { font-size: 11px; color: var(--text-3); }
.ab-me-value { font-size: 24px; font-weight: 800; }
.ab-me-note { font-size: 11px; color: var(--gold); margin-top: 2px; }

.npc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 14px;
}

.npc-card {
  background: linear-gradient(180deg, #101a2e, #0d1524);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 16px 10px;
  cursor: pointer;
  transition: transform 0.15s, border-color 0.15s;
}

.npc-card:hover { transform: translateY(-3px); border-color: #6d5ef7; }
.npc-card.rank-1 { border-color: rgba(124, 108, 255, 0.6); }

.nc-top { display: flex; align-items: center; gap: 12px; }
.nc-avatar { font-size: 30px; }
.nc-id { flex: 1; }
.nc-name { font-weight: 700; font-size: 15px; display: flex; align-items: center; gap: 6px; }
.rank-badge {
  font-size: 11px; width: 18px; height: 18px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  background: #26263a; color: var(--text-2); font-weight: 700;
}
.rank-badge.r1 { background: #8b7cff; color: #0c0c14; }
.rank-badge.r2 { background: #a9b6cc; color: #0c0c14; }
.rank-badge.r3 { background: #c88a5a; color: #fff; }
.nc-title { font-size: 11px; color: var(--text-3); font-weight: 400; }
.nc-style { font-size: 12px; color: var(--text-3); margin-top: 2px; }
.nc-return { font-size: 20px; font-weight: 800; }

.nc-stats {
  display: flex; gap: 16px;
  font-size: 12px; color: var(--text-3);
  margin: 8px 0 4px;
}
.nc-stats b { color: var(--text-1); font-weight: 600; }

.nc-curve { height: 52px; margin: 2px -6px 6px; }

.nc-action {
  display: flex; align-items: center; gap: 8px;
  border-top: 1px dashed var(--border);
  padding-top: 8px; font-size: 12px;
}
.nc-action-text { flex: 1; color: var(--text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.nc-action-date { color: var(--text-3); font-size: 11px; }

.dt-bio { display: flex; gap: 14px; align-items: center; margin-bottom: 14px; }
.dt-avatar { font-size: 42px; }
.dt-bio .sub { color: var(--text-3); font-size: 12px; margin-left: 8px; }
.dt-quote { font-size: 13px; color: var(--text-2); margin-top: 4px; }
.dt-sec { font-weight: 700; margin: 14px 0 8px; }
</style>

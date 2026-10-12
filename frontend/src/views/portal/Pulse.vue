<template>
  <div v-loading="loading">
    <!-- 指数卡 -->
    <el-row :gutter="14">
      <el-col v-for="idx in indexes" :key="idx.name" :span="6">
        <el-card shadow="hover" class="idx-card">
          <div class="idx-name">{{ idx.name }}</div>
          <div class="idx-value num" :class="idx.change_pct > 0 ? 'up' : idx.change_pct < 0 ? 'down' : 'flat'">
            {{ idx.price.toLocaleString() }}
          </div>
          <el-tag :type="idx.change_pct > 0 ? 'danger' : 'success'" effect="dark" size="small" class="num">
            {{ idx.change_pct > 0 ? '+' : '' }}{{ idx.change_pct }}%
          </el-tag>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="14" style="margin-top: 14px">
      <!-- 涨跌家数 + 温度 -->
      <el-col :span="8">
        <el-card shadow="never" class="full-h">
          <template #header><div class="panel-title">市场宽度（平台股票池）</div></template>
          <div class="breadth">
            <div class="b-item up">
              <b class="num">{{ breadth.up }}</b><span>上涨</span>
            </div>
            <div class="b-item flat">
              <b class="num">{{ breadth.flat }}</b><span>平盘</span>
            </div>
            <div class="b-item down">
              <b class="num">{{ breadth.down }}</b><span>下跌</span>
            </div>
          </div>
          <el-progress
            :percentage="breadth.total ? Math.round(breadth.up / breadth.total * 100) : 0"
            :color="'#ff5b66'"
            :stroke-width="12"
            :format="(p) => p + '% 上涨占比'"
          />
          <el-divider>快讯情绪</el-divider>
          <div class="senti" v-if="newsTemp">
            市场情绪
            <b :class="newsTemp === '偏暖' ? 'up' : newsTemp === '偏冷' ? 'down' : 'flat'">{{ newsTemp }}</b>
            <span class="s-detail">利好 {{ sStat['利好'] ?? 0 }} / 利空 {{ sStat['利空'] ?? 0 }} / 中性 {{ sStat['中性'] ?? 0 }}</span>
          </div>
        </el-card>
      </el-col>

      <!-- 涨幅榜 / 跌幅榜 -->
      <el-col :span="16">
        <el-card shadow="never" class="full-h">
          <template #header><div class="panel-title">实时涨跌榜（24 只标的）</div></template>
          <el-row :gutter="16">
            <el-col :span="12">
              <div class="rank-title up">涨幅榜</div>
              <div v-for="(s, i) in gainers" :key="'g' + i" class="rank-row">
                <span class="rk">{{ i + 1 }}</span>
                <b>{{ s.name }}</b>
                <span class="sub">{{ s.code }}</span>
                <span class="num r-price">{{ s.price }}</span>
                <el-tag type="danger" effect="dark" size="small" class="num">{{ s.change_pct > 0 ? '+' : '' }}{{ s.change_pct }}%</el-tag>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="rank-title down">跌幅榜</div>
              <div v-for="(s, i) in losers" :key="'l' + i" class="rank-row">
                <span class="rk">{{ i + 1 }}</span>
                <b>{{ s.name }}</b>
                <span class="sub">{{ s.code }}</span>
                <span class="num r-price">{{ s.price }}</span>
                <el-tag type="success" effect="dark" size="small" class="num">{{ s.change_pct }}%</el-tag>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <!-- 强势榜 -->
    <el-card shadow="never" style="margin-top: 14px">
      <template #header><div class="panel-title">距 60 日高点强度榜（越接近 0 越接近创新高）</div></template>
      <el-table :data="strength" size="large">
        <el-table-column type="index" label="#" width="60" />
        <el-table-column prop="code" label="代码" width="100" />
        <el-table-column prop="name" label="名称" width="130" />
        <el-table-column label="现价" width="110" align="right">
          <template #default="{ row }"><span class="num">{{ row.price }}</span></template>
        </el-table-column>
        <el-table-column label="距 60 日高点" min-width="260">
          <template #default="{ row }">
            <el-progress
              :percentage="Math.min(Math.abs(row.off_high) * 4, 100)"
              :color="row.off_high > -3 ? '#ff5b66' : row.off_high > -10 ? '#e6a23c' : '#00c98d'"
              :stroke-width="10"
              :format="() => row.off_high + '%'"
            />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.off_high > -3 ? 'danger' : row.off_high > -10 ? 'warning' : 'success'" size="small">
              {{ row.off_high > -3 ? '临近新高' : row.off_high > -10 ? '中位' : '深度回调' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import api from '../../api'

const loading = ref(true)
const indexes = ref([])
const breadth = ref({ up: 0, down: 0, flat: 0, total: 0 })
const gainers = ref([])
const losers = ref([])
const strength = ref([])
const newsTemp = ref('')
const sStat = ref({})
let timer = null

async function load() {
  const [pulse, news] = await Promise.all([api.get('/analysis/market'), api.get('/news/sentiment')])
  indexes.value = pulse.indexes
  breadth.value = pulse.breadth
  gainers.value = pulse.gainers
  losers.value = pulse.losers
  strength.value = pulse.strength_top
  newsTemp.value = news.temperature
  sStat.value = news.stat
}

onMounted(async () => {
  try {
    await load()
    timer = setInterval(load, 15000)
  } finally {
    loading.value = false
  }
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.idx-card { border-radius: 10px; }
.idx-name { font-size: 12px; color: var(--text-2); }
.idx-value { font-size: 26px; font-weight: 800; margin: 4px 0 6px; }

.full-h { height: 100%; }

.breadth { display: flex; justify-content: space-between; margin-bottom: 16px; }
.b-item { text-align: center; display: flex; flex-direction: column; gap: 4px; }
.b-item b { font-size: 30px; font-weight: 800; }
.b-item span { font-size: 12px; color: var(--text-3); }

.senti { font-size: 14px; color: var(--text-1); }
.s-detail { font-size: 12px; color: var(--text-3); margin-left: 10px; }

.rank-title { font-weight: 700; margin-bottom: 8px; }
.rank-row {
  display: flex; align-items: center; gap: 10px;
  padding: 7px 0; border-bottom: 1px dashed var(--border);
  font-size: 13px;
}
.rk { color: var(--text-3); width: 16px; }
.sub { color: var(--text-3); font-size: 11px; }
.r-price { margin-left: auto; color: var(--text-1); }
</style>

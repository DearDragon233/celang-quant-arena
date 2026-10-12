<template>
  <div v-loading="loading">
    <div class="news-banner">
      <div class="nb-left">
        <el-icon :size="26" color="#8b7cff"><Bell /></el-icon>
        <div>
          <div class="nb-title">财经快讯</div>
          <div class="nb-sub">
            自动追踪 {{ cutoff }}（昨日收盘）以来的全部市场消息 · 双源合并（东方财富 7×24 + 新浪财经滚动）· 60 秒自动刷新
          </div>
        </div>
      </div>
      <div class="sentiment-box">
        <div class="s-item">
          <span class="s-label">利好</span>
          <b class="num up">{{ sentiment.stat?.['利好'] ?? 0 }}</b>
        </div>
        <div class="s-item">
          <span class="s-label">利空</span>
          <b class="num down">{{ sentiment.stat?.['利空'] ?? 0 }}</b>
        </div>
        <div class="s-item">
          <span class="s-label">中性</span>
          <b class="num flat">{{ sentiment.stat?.['中性'] ?? 0 }}</b>
        </div>
        <div class="s-temp">
          市场情绪
          <b :class="sentiment.temperature === '偏暖' ? 'up' : sentiment.temperature === '偏冷' ? 'down' : 'flat'">
            {{ sentiment.temperature }}
          </b>
        </div>
        <el-tag effect="dark" type="warning" size="large">昨日收盘以来新增 {{ total }} 条</el-tag>
      </div>
    </div>

    <el-card shadow="never">
      <div class="filter-row">
        <el-radio-group v-model="filter" size="default">
          <el-radio-button value="all">全部（{{ total }}）</el-radio-button>
          <el-radio-button value="cn">A股相关（{{ countCn }}）</el-radio-button>
          <el-radio-button value="us">美股相关（{{ countUs }}）</el-radio-button>
        </el-radio-group>
        <el-button link type="primary" :loading="loading" @click="load">手动刷新</el-button>
      </div>

      <div class="timeline">
        <div v-for="(n, idx) in filtered" :key="idx" class="news-item" :class="'s-' + n.sentiment">
          <div class="ni-sentiment" :class="sentCls(n.sentiment)">{{ n.sentiment }}</div>
          <div class="ni-time num">{{ n.time.slice(5, 16) }}</div>
          <div class="ni-body">
            <div class="ni-title">
              <el-tag v-if="tagOf(n) === 'cn'" size="small" effect="plain" type="danger">A股</el-tag>
              <el-tag v-else-if="tagOf(n) === 'us'" size="small" effect="plain" type="warning">美股</el-tag>
              <a v-if="n.url" :href="n.url" target="_blank" rel="noopener">{{ n.title }}</a>
              <span v-else>{{ n.title }}</span>
            </div>
            <div class="ni-summary" v-if="n.summary">{{ n.summary }}</div>
            <div class="ni-source">来源：{{ n.source }}</div>
          </div>
        </div>
        <el-empty v-if="!loading && !filtered.length" description="暂无快讯" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import api from '../../api'

const loading = ref(true)
const items = ref([])
const total = ref(0)
const cutoff = ref('')
const sentiment = ref({ stat: {}, temperature: '平稳' })
const filter = ref('all')
let timer = null

const CN_KEYS = ['A股', '股市', '证监会', '沪深', '券商', '发改委', '央行', '人民币', '证监会', '上证', '深证', '北向', '基金', '上市公司', 'IPO', '板块']
const US_KEYS = ['美股', '美联储', '纳斯达克', '纳斯达克', '道琼斯', '标普', '苹果', '特斯拉', '英伟达', '微软', '美元', 'Fed', '纳斯']

function sentCls(s) {
  return s === '利好' ? 'sent-bull' : s === '利空' ? 'sent-bear' : 'sent-neutral'
}

function tagOf(n) {
  const text = n.title + n.summary
  if (US_KEYS.some((k) => text.includes(k))) return 'us'
  if (CN_KEYS.some((k) => text.includes(k))) return 'cn'
  return 'other'
}

const filtered = computed(() => {
  if (filter.value === 'all') return items.value
  return items.value.filter((n) => tagOf(n) === filter.value)
})
const countCn = computed(() => items.value.filter((n) => tagOf(n) === 'cn').length)
const countUs = computed(() => items.value.filter((n) => tagOf(n) === 'us').length)

async function load() {
  const data = await api.get('/news/list?limit=80&since_close=1')
  items.value = data.items
  total.value = data.total
  cutoff.value = data.cutoff
  sentiment.value = data.sentiment || { stat: {}, temperature: '平稳' }
}

onMounted(async () => {
  try {
    await load()
    timer = setInterval(load, 60000)
  } finally {
    loading.value = false
  }
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.news-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(120deg, #15151f, #0e1626);
  border: 1px solid #2c2c40;
  border-radius: 12px;
  padding: 16px 24px;
  margin-bottom: 16px;
}

.nb-left { display: flex; align-items: center; gap: 14px; }
.nb-title { font-size: 18px; font-weight: 800; color: #fff; }
.nb-sub { font-size: 12px; color: var(--text-2); margin-top: 4px; }

.filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.timeline { display: flex; flex-direction: column; }

.sentiment-box {
  display: flex;
  align-items: center;
  gap: 18px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  padding: 8px 18px;
}

.s-item { text-align: center; }
.s-label { display: block; font-size: 10px; color: var(--text-3); }
.s-item b { font-size: 18px; }
.s-temp { font-size: 12px; color: var(--text-2); margin-right: 4px; }
.s-temp b { font-size: 15px; margin-left: 4px; }

.news-item.s-利好 { border-left: 3px solid #ff5b66; padding-left: 10px; }
.news-item.s-利空 { border-left: 3px solid #00c98d; padding-left: 10px; }
.news-item.s-中性 { border-left: 3px solid #2c2c40; padding-left: 10px; }

.ni-sentiment {
  width: 46px; flex-shrink: 0; text-align: center;
  font-size: 12px; font-weight: 700; padding: 3px 0;
  border-radius: 6px; align-self: flex-start; margin-top: 2px;
}
.sent-bull { color: #ff5b66; background: rgba(255, 91, 102, 0.12); }
.sent-bear { color: #00c98d; background: rgba(0, 201, 141, 0.12); }
.sent-neutral { color: var(--text-3); background: rgba(255, 255, 255, 0.05); }

.news-item {
  display: flex;
  gap: 18px;
  padding: 12px 4px;
  border-bottom: 1px solid #16213a;
}

.ni-time { width: 90px; color: var(--text-3); font-size: 12.5px; padding-top: 3px; flex-shrink: 0; }

.ni-body { flex: 1; }
.ni-title { font-size: 14.5px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.ni-title a { color: var(--text-1); text-decoration: none; }
.ni-title a:hover { color: var(--gold); }
.ni-summary {
  font-size: 12.5px;
  color: var(--text-2);
  margin-top: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ni-source { font-size: 11px; color: var(--text-3); margin-top: 4px; }
</style>

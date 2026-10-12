<template>
  <div v-loading="loading">
    <!-- 大赛横幅 -->
    <div class="comp-banner">
      <div class="cb-left">
        <el-icon :size="30" color="#8b7cff"><Trophy /></el-icon>
        <div>
          <div class="cb-name">{{ settings.comp_name }} <el-tag effect="dark" size="small" type="primary">{{ settings.comp_season }}</el-tag></div>
          <div class="cb-time">年度场长期有效 · 管理员发布的限时比赛可在下方报名，资金独立核算</div>
        </div>
      </div>
    </div>

    <!-- 比赛窗口 -->
    <el-card shadow="never" class="contest-card">
      <template #header><div class="panel-title">比赛窗口（报名后获得独立资金账户，与年度场隔离）</div></template>
      <el-empty v-if="!contests.length" description="暂无进行中的比赛，等待组委会发布" :image-size="70" />
      <div class="contest-grid">
        <div v-for="c in contests" :key="c.id" class="contest-item">
          <div class="ci-top">
            <span class="ci-name">{{ c.name }}</span>
            <el-tag :type="statusType(c.status_text)" effect="dark" size="small">{{ c.status_text }}</el-tag>
          </div>
          <div class="ci-desc">{{ c.description }}</div>
          <div class="ci-meta">
            <span>赛程 {{ c.start_date.slice(0, 10) }} ~ {{ c.end_date.slice(0, 10) }}</span>
            <span>初始资金 {{ num(c.initial_cash) }}</span>
            <span>{{ c.entry_count }} 人报名</span>
          </div>
          <div class="ci-foot">
            <template v-if="c.joined">
              <span class="ci-mine">
                我的收益
                <b class="num" :class="c.my_return_pct > 0 ? 'up' : c.my_return_pct < 0 ? 'down' : 'flat'">
                  {{ c.my_return_pct > 0 ? '+' : '' }}{{ c.my_return_pct }}%
                </b>
              </span>
              <el-button type="primary" size="small" round :disabled="!c.ongoing" @click="viewContest(c)">
                进入排行
              </el-button>
            </template>
            <template v-else>
              <span class="ci-mine">未报名</span>
              <el-button
                type="primary"
                size="small"
                round
                :disabled="c.status_text !== '未开始' && c.status_text !== '进行中'"
                @click="join(c)"
              >
                立即报名
              </el-button>
            </template>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 排行 -->
    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <div class="panel-title">{{ boardTitle }}</div>
      </template>
      <el-table :data="list" size="large" :row-class-name="rowClass">
        <el-table-column label="排名" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.rank === 1" class="medal gold">🥇 1</span>
            <span v-else-if="row.rank === 2" class="medal silver">🥈 2</span>
            <span v-else-if="row.rank === 3" class="medal bronze">🥉 3</span>
            <span v-else class="num rank-num">{{ row.rank }}</span>
          </template>
        </el-table-column>
        <el-table-column label="选手" min-width="160">
          <template #default="{ row }">
            <b>{{ row.nickname }}</b>
            <span class="sub">{{ row.school }}</span>
            <el-tag v-if="row.user_id === store.user?.id" size="small" type="primary" effect="dark" class="me-tag">我</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="总资产" width="150" align="right">
          <template #default="{ row }"><span class="num">{{ num(row.total) }}</span></template>
        </el-table-column>
        <el-table-column label="总收益率" width="130" align="right">
          <template #default="{ row }">
            <b class="num" :class="row.return_pct > 0 ? 'up' : row.return_pct < 0 ? 'down' : 'flat'">
              {{ row.return_pct > 0 ? '+' : '' }}{{ row.return_pct }}%
            </b>
          </template>
        </el-table-column>
        <el-table-column label="收益率条" min-width="170">
          <template #default="{ row }">
            <el-progress
              :percentage="Math.min(Math.abs(row.return_pct) * 5, 100)"
              :color="row.return_pct >= 0 ? '#ff5b66' : '#00c98d'"
              :stroke-width="8"
              :show-text="false"
            />
          </template>
        </el-table-column>
      </el-table>
      <div class="updated">数据更新于 {{ updatedAt }} · 实时行情估值 · 10 秒刷新</div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'
import { useUserStore } from '../../stores/user'

const store = useUserStore()
const loading = ref(true)
const contests = ref([])
const settings = ref({ comp_name: '模拟炒股大赛', comp_season: '' })
const list = ref([])
const updatedAt = ref('')
const currentContest = ref(null) // null = 年度场
let timer = null

const boardTitle = computed(() =>
  currentContest.value
    ? `${currentContest.value.name} · 比赛排行`
    : '年度场排行（常驻账户，长期有效）'
)

function num(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function statusType(t) {
  return { 进行中: 'success', 未开始: 'primary', 已结束: 'info', 未发布: 'info' }[t] || 'info'
}
function rowClass({ row }) {
  return row.is_me ? 'my-row' : ''
}

async function loadContests() {
  const data = await api.get('/contests/window')
  contests.value = data.contests
  if (currentContest.value) {
    currentContest.value = data.contests.find((c) => c.id === currentContest.value.id) || null
  }
}

async function loadBoard() {
  let data
  if (currentContest.value) {
    data = await api.get(`/contests/${currentContest.value.id}/leaderboard`)
  } else {
    data = await api.get('/competition/leaderboard')
  }
  list.value = data.list.map((r) => ({ ...r, is_me: r.user_id === store.user?.id }))
  updatedAt.value = (data.updated_at || '').slice(11, 19)
}

function viewContest(c) {
  currentContest.value = c
  loadBoard()
}

async function join(c) {
  const r = await api.post(`/contests/${c.id}/join`)
  ElMessage.success(r.message || '报名成功')
  await loadContests()
}

onMounted(async () => {
  try {
    await loadContests()
    await loadBoard()
    timer = setInterval(async () => {
      await Promise.all([loadContests(), loadBoard()])
    }, 10000)
  } finally {
    loading.value = false
  }
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.comp-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background:
    radial-gradient(600px 200px at 90% 0%, rgba(124, 108, 255, 0.16), transparent),
    linear-gradient(120deg, #15151f, #0e0e16);
  border: 1px solid #2c2c40;
  border-radius: 12px;
  padding: 18px 24px;
  margin-bottom: 16px;
}

.cb-left { display: flex; align-items: center; gap: 16px; }
.cb-name { font-size: 19px; font-weight: 800; color: #fff; display: flex; align-items: center; gap: 10px; }
.cb-time { font-size: 12px; color: var(--text-2); margin-top: 4px; }

.contest-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  gap: 14px;
}

.contest-item {
  background: var(--bg-panel-2);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
}

.ci-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.ci-name { font-weight: 700; font-size: 15px; }
.ci-desc { font-size: 12px; color: var(--text-2); margin: 6px 0; line-height: 1.6; }
.ci-meta { display: flex; gap: 14px; font-size: 12px; color: var(--text-3); flex-wrap: wrap; }
.ci-foot {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 10px; padding-top: 10px;
  border-top: 1px dashed var(--border);
}
.ci-mine { font-size: 13px; color: var(--text-2); }

.sub { color: var(--text-3); font-size: 12px; margin-left: 8px; }
.me-tag { margin-left: 8px; }
.medal { font-size: 16px; font-weight: 700; }
.medal.gold { color: #a78bfa; }
.medal.silver { color: #c9d3e4; }
.medal.bronze { color: #e0a678; }
.rank-num { color: var(--text-2); }
.updated { margin-top: 10px; font-size: 12px; color: var(--text-3); text-align: right; }
:deep(.my-row) { background: rgba(124, 108, 255, 0.08) !important; }
</style>

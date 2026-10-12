<template>
  <div v-loading="loading" class="advisor">
    <!-- 大盘环境 -->
    <div class="regime-row">
      <div v-for="(r, key) in regime" :key="key" class="regime-card">
        <div class="regime-name">{{ r.index_name }}</div>
        <div class="regime-close num">{{ r.close }}</div>
        <div class="regime-meta">20日 <span :class="r.chg20 > 0 ? 'up' : 'down'">{{ r.chg20 > 0 ? '+' : '' }}{{ r.chg20 }}%</span> · MA20 {{ r.ma20 }}</div>
        <el-tag :type="r.regime === '偏多' ? 'danger' : r.regime === '偏空' ? 'success' : 'info'" effect="dark" size="small">
          {{ r.regime }}环境
        </el-tag>
      </div>
      <div class="regime-card root-card">
        <div class="regime-name">综合判定</div>
        <div class="regime-root">{{ root.title.replace('当前市场环境：', '') }}</div>
        <div class="regime-meta">{{ root.desc }}</div>
      </div>
    </div>

    <el-row :gutter="16">
      <!-- 左：今日雷达 -->
      <el-col :span="9">
        <el-card shadow="never">
          <template #header><div class="panel-title">今日策略雷达（全部标的信号评分）</div></template>
          <el-table
            :data="radar"
            size="large"
            highlight-current-row
            style="cursor: pointer"
            @row-click="(row) => scrollTo(row.stock_id)"
          >
            <el-table-column prop="rank" label="#" width="50">
              <template #default="{ $index }">{{ $index + 1 }}</template>
            </el-table-column>
            <el-table-column label="标的" min-width="130">
              <template #default="{ row }">
                <b>{{ row.name }}</b>
                <span class="sub">{{ row.code }}</span>
                <el-tag size="small" :type="row.market === 'CN' ? '' : 'warning'" effect="plain" class="mkt">
                  {{ row.market === 'CN' ? 'A股' : '美股' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="评级" width="110">
              <template #default="{ row }">
                <el-tag :type="badgeType(row.verdict)" effect="dark" size="small">{{ row.verdict }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="评分" width="80" align="right">
              <template #default="{ row }">
                <b class="num" :class="row.score >= 60 ? 'up' : row.score < 40 ? 'down' : 'flat'">{{ row.score }}</b>
              </template>
            </el-table-column>
            <el-table-column label="RSI" width="65" align="right">
              <template #default="{ row }"><span class="num sub2">{{ row.rsi }}</span></template>
            </el-table-column>
            <el-table-column label="20日动量" width="90" align="right">
              <template #default="{ row }">
                <span class="num" :class="row.mom20 > 0 ? 'up' : 'down'">{{ row.mom20 > 0 ? '+' : '' }}{{ row.mom20 }}%</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 右：决策树 -->
      <el-col :span="15">
        <el-card shadow="never">
          <template #header>
            <div class="panel-title">投资决策树（按分支展开，点击决策卡可直接执行）</div>
          </template>
          <div class="tree">
            <!-- 根 -->
            <div class="tree-root">
              <el-icon :size="18" color="#8b7cff"><Guide /></el-icon>
              <div>
                <div class="t-title">{{ root.title }}</div>
                <div class="t-desc">{{ root.desc }}</div>
              </div>
            </div>
            <!-- 分支 -->
            <div v-for="branch in root.children" :key="branch.id" class="branch">
              <div class="branch-head">
                <span class="b-name">{{ branch.title }}</span>
                <span class="b-desc">{{ branch.desc }}</span>
                <el-tag size="small" effect="plain">{{ branch.children.length }} 个决策</el-tag>
              </div>
              <div class="cards">
                <div v-for="node in branch.children" :key="node.id" class="decision-card" :id="'card-' + stockIdOf(node)">
                  <div class="d-head">
                    <span class="d-title">{{ node.title }}</span>
                    <el-tag :type="badgeType(node.badge)" size="small" effect="dark">{{ node.badge }}</el-tag>
                  </div>
                  <div class="d-body" v-if="node.leaf">
                    <div class="leaf-grid" v-if="node.leaf.action !== '纪律执行' && node.leaf.action !== '观望'">
                      <div class="lg-item" v-if="node.leaf.stock"><span>标的</span><b>{{ node.leaf.stock }}</b></div>
                      <div class="lg-item"><span>建议仓位</span><b>{{ node.leaf.position }}</b></div>
                      <div class="lg-item" v-if="node.leaf.entry"><span>参考入场</span><b class="num">{{ node.leaf.entry }}</b></div>
                      <div class="lg-item" v-if="node.leaf.stop"><span>止损纪律</span><b class="down">{{ node.leaf.stop }}</b></div>
                      <div class="lg-item" v-if="node.leaf.target"><span>止盈目标</span><b class="up">{{ node.leaf.target }}</b></div>
                    </div>
                    <div class="basis">
                      <el-tag v-for="b in node.leaf.basis" :key="b" size="small" effect="plain" class="basis-tag">{{ b }}</el-tag>
                    </div>
                    <div class="d-foot" v-if="node.leaf.stock_id">
                      <span class="conf">置信度 <b class="num">{{ node.score }}</b>/100</span>
                      <el-button type="primary" size="small" round @click="execute(node.leaf)">
                        <el-icon><Lightning /></el-icon>&nbsp;去执行
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'

const router = useRouter()
const loading = ref(true)
const regime = ref({})
const root = ref({ title: '', desc: '', children: [] })
const radar = ref([])

function badgeType(v) {
  if (['强势可做多', '短线买入', '分批买入', '超卖低吸'].includes(v)) return 'danger'
  if (['逢高兑现', '回避减仓'].includes(v)) return 'success'
  return 'info'
}

function stockIdOf(node) {
  return node.leaf?.stock_id || node.id
}

function scrollTo(stockId) {
  const el = document.getElementById('card-' + stockId)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function execute(leaf) {
  router.push({ path: '/portal/trade', query: { stock_id: leaf.stock_id } })
}

onMounted(async () => {
  try {
    const data = await api.get('/advisor/tree')
    regime.value = data.regime
    root.value = data.root
    radar.value = data.radar
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.regime-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}

.regime-card {
  background: linear-gradient(145deg, #131e33, #0e1626);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px 18px;
}

.root-card {
  background: linear-gradient(145deg, #17171f, #131e33);
  border-color: #2c2c40;
}

.regime-name {
  font-size: 12px;
  color: var(--text-2);
}

.regime-close {
  font-size: 26px;
  font-weight: 800;
  margin: 4px 0 2px;
}

.regime-root {
  font-size: 22px;
  font-weight: 800;
  color: var(--gold);
  margin: 4px 0 2px;
}

.regime-meta {
  font-size: 12px;
  color: var(--text-3);
  margin-bottom: 8px;
}

.sub { color: var(--text-3); font-size: 12px; margin-left: 6px; }
.sub2 { color: var(--text-2); }
.mkt { margin-left: 6px; }

.tree-root {
  display: flex;
  gap: 12px;
  align-items: center;
  background: linear-gradient(120deg, rgba(124, 108, 255, 0.12), rgba(79, 139, 255, 0.08));
  border: 1px solid #2c2c40;
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 16px;
}

.t-title { font-size: 16px; font-weight: 700; color: var(--gold); }
.t-desc { font-size: 12px; color: var(--text-2); margin-top: 3px; }

.branch { margin-bottom: 18px; }

.branch-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 4px;
  border-bottom: 1px dashed var(--border);
  margin-bottom: 12px;
}

.b-name { font-weight: 700; font-size: 14px; color: var(--text-1); }
.b-desc { font-size: 12px; color: var(--text-3); flex: 1; }

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}

.decision-card {
  background: var(--bg-panel-2);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
  transition: border-color 0.2s, transform 0.2s;
}

.decision-card:hover {
  border-color: #6d5ef7;
  transform: translateY(-2px);
}

.d-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.d-title { font-size: 13.5px; font-weight: 700; }

.leaf-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; margin-bottom: 8px; }

.lg-item { font-size: 12px; display: flex; flex-direction: column; gap: 1px; }
.lg-item span { color: var(--text-3); }
.lg-item b { font-weight: 600; font-size: 12.5px; }

.basis { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.basis-tag { font-size: 11px; }

.d-foot { display: flex; justify-content: space-between; align-items: center; }
.conf { font-size: 12px; color: var(--text-2); }
.conf b { color: var(--gold); }
</style>

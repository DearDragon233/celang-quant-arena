<template>
  <el-container class="portal app-bg">
    <el-header class="portal-header">
      <div class="brand" @click="$router.push('/portal/market')">
        <img :src="logoUrl" class="brand-logo" alt="策澜" />
        <div>
          <div class="brand-name">策澜量化竞技场</div>
          <div class="brand-sub">真实行情 · 模拟大赛</div>
        </div>
      </div>
      <el-menu mode="horizontal" :default-active="activeMenu" router :ellipsis="false" class="nav">
        <el-menu-item index="/portal/overview"><el-icon><Wallet /></el-icon>资产总览</el-menu-item>
        <el-menu-item index="/portal/market"><el-icon><TrendCharts /></el-icon>行情中心</el-menu-item>
        <el-menu-item index="/portal/pulse"><el-icon><DataLine /></el-icon>场内分析</el-menu-item>
        <el-menu-item index="/portal/trade"><el-icon><Switch /></el-icon>模拟交易</el-menu-item>
        <el-menu-item index="/portal/holdings"><el-icon><PieChart /></el-icon>持仓分析</el-menu-item>
        <el-menu-item index="/portal/pnl"><el-icon><Histogram /></el-icon>收益分析</el-menu-item>
        <el-menu-item index="/portal/advisor"><el-icon><Guide /></el-icon>策略决策树</el-menu-item>
        <el-menu-item index="/portal/quant"><el-icon><Cpu /></el-icon>量化回测</el-menu-item>
        <el-menu-item index="/portal/npc"><el-icon><Aim /></el-icon>NPC竞技场</el-menu-item>
        <el-menu-item index="/portal/news"><el-icon><Bell /></el-icon>财经快讯</el-menu-item>
        <el-menu-item index="/portal/ranking"><el-icon><Trophy /></el-icon>大赛排行</el-menu-item>
      </el-menu>
      <div class="right">
        <el-select
          v-model="accountLabel"
          size="default"
          class="account-select"
          @change="onAccountChange"
        >
          <el-option label="年度场（常驻账户）" :value="0" />
          <el-option
            v-for="c in joinedContests"
            :key="c.id"
            :value="c.id"
            :label="`比赛 · ${c.name}`"
            :disabled="!c.joined"
          />
        </el-select>
        <div class="equity-box">
          <span class="equity-label">总资产</span>
          <span class="equity-value num">{{ fmt(equity) }}</span>
        </div>
        <el-dropdown @command="onCommand">
          <span class="user-info">
            <el-avatar :size="34" class="avatar">{{ avatarText }}</el-avatar>
            <span class="username">{{ store.user?.nickname }}</span>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout"><el-icon><SwitchButton /></el-icon>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <el-main class="portal-main">
      <router-view @refresh="loadEquity" />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import api from '../api'
import logoUrl from '../assets/logo.jpg'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const store = useUserStore()
const equity = ref(0)
const joinedContests = ref([])
let timer = null

const accountLabel = computed({
  get: () => store.contest?.id ?? 0,
  set: () => {},
})

async function loadContests() {
  try {
    const data = await api.get('/contests/window')
    joinedContests.value = data.contests.filter((c) => c.joined)
  } catch { /* 忽略 */ }
}

function onAccountChange(v) {
  const c = joinedContests.value.find((x) => x.id === v)
  store.setContest(c ? { id: c.id, name: c.name } : null)
  loadEquity()
  window.dispatchEvent(new CustomEvent('account-changed'))
}

const activeMenu = computed(() => '/' + route.path.split('/').slice(1, 3).join('/'))
const avatarText = computed(() => (store.user?.nickname || '客').charAt(0))

function fmt(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadEquity() {
  try {
    const cid = store.contest?.id || 0
    const acct = await api.get(`/trade/account?contest_id=${cid}`)
    equity.value = acct.total
  } catch { /* 忽略 */ }
}

async function onCommand(cmd) {
  if (cmd === 'logout') {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', { type: 'warning' })
    store.logout()
    router.push('/login')
  }
}

onMounted(() => {
  loadContests()
  loadEquity()
  timer = setInterval(loadEquity, 8000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.portal { height: 100%; flex-direction: column; }

.portal-header {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(10, 15, 24, 0.85);
  border-bottom: 1px solid var(--border);
  padding: 0 26px;
  backdrop-filter: blur(8px);
}

.brand { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.brand-logo { width: 38px; height: 38px; border-radius: 50%; border: 2px solid rgba(124,108,255,.5); }
.brand-name { font-size: 16px; font-weight: 800; letter-spacing: 1px; color: #fff; white-space: nowrap; }
.brand-sub { font-size: 10px; color: var(--text-3); letter-spacing: 1px; white-space: nowrap; }

.nav { flex: 1; background: transparent; border-bottom: none; }
.nav :deep(.el-menu-item) {
  color: var(--text-2);
  font-weight: 600;
  border-bottom: 2px solid transparent;
  background: transparent;
  padding: 0 10px;
  white-space: nowrap;
}
.nav :deep(.el-menu-item.is-active) {
  color: var(--gold);
  background: rgba(124, 108, 255, 0.08);
  border-bottom-color: var(--gold);
}
.nav :deep(.el-menu-item:hover) { background: rgba(255, 255, 255, 0.04); color: #fff; }

.right { display: flex; align-items: center; gap: 14px; }

.account-select { width: 150px; }
.account-select :deep(.el-select__wrapper) {
  background: rgba(255, 255, 255, 0.05);
  box-shadow: 0 0 0 1px #2c2c40 inset;
  color: #e8eef8;
}

.equity-box {
  text-align: right;
  background: rgba(124, 108, 255, 0.1);
  border: 1px solid rgba(124, 108, 255, 0.35);
  border-radius: 8px;
  padding: 4px 14px;
}
.equity-label { display: block; font-size: 10px; color: var(--gold); letter-spacing: 2px; }
.equity-value { font-size: 16px; font-weight: 700; color: var(--gold-2); }

.user-info { display: flex; align-items: center; gap: 10px; cursor: pointer; outline: none; }
.username { color: var(--text-1); font-size: 14px; white-space: nowrap; }
.avatar { background: linear-gradient(135deg, #8b7cff, #6d5ef7); color: #0c0c14; font-weight: 700; }

.portal-main { padding: 18px 26px; overflow: auto; }
</style>

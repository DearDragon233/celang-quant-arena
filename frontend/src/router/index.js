import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const adminChildren = [
  {
    path: 'dashboard',
    name: 'dashboard',
    component: () => import('../views/admin/Dashboard.vue'),
    meta: { title: '运营看板', icon: 'Odometer' },
  },
  {
    path: 'users',
    name: 'users',
    component: () => import('../views/admin/Users.vue'),
    meta: { title: '用户管理', icon: 'User' },
  },
  {
    path: 'stocks',
    name: 'stocks',
    component: () => import('../views/admin/Stocks.vue'),
    meta: { title: '股票池管理', icon: 'Coin' },
  },
  {
    path: 'orders',
    name: 'orders',
    component: () => import('../views/admin/Orders.vue'),
    meta: { title: '全局成交', icon: 'List' },
  },
  {
    path: 'settings',
    name: 'settings',
    component: () => import('../views/admin/Settings.vue'),
    meta: { title: '赛程设置', icon: 'Setting' },
  },
  {
    path: 'contest-mgmt',
    name: 'contest-mgmt',
    component: () => import('../views/admin/ContestMgmt.vue'),
    meta: { title: '比赛发布', icon: 'Flag' },
  },
]

const portalChildren = [
  {
    path: 'overview',
    name: 'overview',
    component: () => import('../views/portal/Overview.vue'),
    meta: { title: '资产总览', icon: 'Wallet' },
  },
  {
    path: 'market',
    name: 'market',
    component: () => import('../views/portal/Market.vue'),
    meta: { title: '行情中心', icon: 'TrendCharts' },
  },
  {
    path: 'pulse',
    name: 'pulse',
    component: () => import('../views/portal/Pulse.vue'),
    meta: { title: '场内分析', icon: 'DataLine' },
  },
  {
    path: 'holdings',
    name: 'holdings',
    component: () => import('../views/portal/Holdings.vue'),
    meta: { title: '持仓分析', icon: 'PieChart' },
  },
  {
    path: 'pnl',
    name: 'pnl',
    component: () => import('../views/portal/Pnl.vue'),
    meta: { title: '收益分析', icon: 'Histogram' },
  },
  {
    path: 'trade',
    name: 'trade',
    component: () => import('../views/portal/Trade.vue'),
    meta: { title: '模拟交易', icon: 'Switch' },
  },
  {
    path: 'quant',
    name: 'quant',
    component: () => import('../views/portal/Quant.vue'),
    meta: { title: '量化回测', icon: 'Cpu' },
  },
  {
    path: 'advisor',
    name: 'advisor',
    component: () => import('../views/portal/Advisor.vue'),
    meta: { title: '策略决策树', icon: 'Guide' },
  },
  {
    path: 'ranking',
    name: 'ranking',
    component: () => import('../views/portal/Ranking.vue'),
    meta: { title: '大赛排行', icon: 'Trophy' },
  },
  {
    path: 'npc',
    name: 'npc',
    component: () => import('../views/portal/NpcArena.vue'),
    meta: { title: 'NPC竞技场', icon: 'Aim' },
  },
  {
    path: 'news',
    name: 'news',
    component: () => import('../views/portal/News.vue'),
    meta: { title: '财经快讯', icon: 'Bell' },
  },
]

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/admin',
    component: () => import('../layout/AdminLayout.vue'),
    redirect: '/admin/dashboard',
    children: adminChildren,
  },
  {
    path: '/portal',
    component: () => import('../layout/PortalLayout.vue'),
    redirect: '/portal/market',
    children: portalChildren,
  },
  { path: '/', redirect: '/login' },
  { path: '/:pathMatch(.*)*', redirect: '/login' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const store = useUserStore()
  if (to.name !== 'login' && !store.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && store.isLoggedIn) {
    return store.user?.role === 'admin' ? { path: '/admin/dashboard' } : { path: '/portal/market' }
  }
  const role = store.user?.role
  if (to.path.startsWith('/portal') && role === 'admin') return { path: '/admin/dashboard' }
  if (to.path.startsWith('/admin') && role !== 'admin') return { path: '/portal/market' }
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} - 策澜量化竞技场` : '策澜量化竞技场'
})

export default router

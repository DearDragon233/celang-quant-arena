<template>
  <el-container class="layout">
    <el-aside width="210px" class="aside">
      <div class="logo">
        <img :src="logoUrl" class="logo-img" alt="策澜" />
        <span>策澜竞技场</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#0b1322"
        text-color="#a3b1c6"
        active-text-color="#ffffff"
        class="menu"
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </el-menu>
      <div class="aside-footer">策澜 · 模拟盘真实行情</div>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>管理端</el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta.title">{{ route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <el-dropdown @command="onCommand">
          <span class="user-info">
            <el-avatar :size="32" class="avatar">{{ avatarText }}</el-avatar>
            <span class="username">{{ store.user?.nickname }}</span>
            <el-tag size="small" type="danger">管理员</el-tag>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '../stores/user'
import logoUrl from '../assets/logo.jpg'

const route = useRoute()
const router = useRouter()
const store = useUserStore()

const menuItems = computed(() =>
  router.options.routes
    .find((r) => r.path === '/admin')
    .children.map((r) => ({ path: '/admin/' + r.path, title: r.meta.title, icon: r.meta.icon }))
)

const activeMenu = computed(() => route.path)
const avatarText = computed(() => (store.user?.nickname || 'A').charAt(0))

async function onCommand(cmd) {
  if (cmd === 'logout') {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', { type: 'warning' })
    store.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout {
  height: 100%;
}

.aside {
  background-color: #0b1322;
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 1px;
}
.logo-img { width: 34px; height: 34px; border-radius: 50%; border: 2px solid rgba(212,175,57,.5); }

.menu {
  border-right: none;
  flex: 1;
}

.aside-footer {
  padding: 14px;
  text-align: center;
  color: #5a6a85;
  font-size: 11px;
}

.header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(10,15,24,0.85);
  border-bottom: 1px solid var(--border);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  outline: none;
}

.username {
  color: var(--text-1);
  font-size: 14px;
}

.avatar {
  background: linear-gradient(135deg, #171722, #6d5ef7);
  color: #fff;
  font-weight: 600;
}

.main {
  background-color: var(--bg);
  padding: 16px;
}
</style>

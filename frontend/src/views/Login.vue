<template>
  <div class="login-page app-bg">
    <div class="login-box">
      <div class="brand">
        <img :src="logoUrl" class="brand-logo" alt="策澜" />
        <h1>策澜量化竞技场</h1>
        <p>全国大学生模拟炒股大赛 · 真实行情模拟交易</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" size="large" @keyup.enter="onSubmit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="参赛账号" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" class="login-btn" :loading="loading" @click="onSubmit">进入赛场</el-button>
        </el-form-item>
      </el-form>
      <div class="tips">
        选手 trader01 ~ trader05 / 123456（初始资金 100 万）<br />
        组委会 admin / admin123
      </div>
      <div class="badges">
        <el-tag effect="dark" type="warning" size="small">A股真实行情</el-tag>
        <el-tag effect="dark" type="danger" size="small">美股真实行情</el-tag>
        <el-tag effect="dark" type="primary" size="small">AI 策略决策树</el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import api from '../api'
import { useUserStore } from '../stores/user'
import logoUrl from '../assets/logo.jpg'

const route = useRoute()
const router = useRouter()
const store = useUserStore()
const formRef = ref()
const loading = ref(false)

const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入参赛账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function onSubmit() {
  await formRef.value.validate()
  loading.value = true
  try {
    const data = await api.post('/auth/login', form)
    store.setSession(data.access_token, data.user)
    ElMessage.success(`欢迎，${data.user.nickname}`)
    const fallback = data.user.role === 'admin' ? '/admin/dashboard' : '/portal/market'
    router.push(route.query.redirect?.startsWith('/') ? route.query.redirect : fallback)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-box {
  width: 430px;
  padding: 42px 38px 26px;
  background: rgba(14, 22, 38, 0.92);
  border: 1px solid #223154;
  border-radius: 16px;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(10px);
}

.brand { text-align: center; margin-bottom: 26px; }
.brand-logo { width: 74px; height: 74px; border-radius: 50%; box-shadow: 0 6px 24px rgba(124,108,255,.35); }
.brand h1 {
  font-size: 22px;
  background: linear-gradient(120deg, #a78bfa, #8b7cff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  margin-top: 12px;
}
.brand p { font-size: 12px; color: var(--text-2); letter-spacing: 3px; margin-top: 6px; }

.login-btn { width: 100%; font-weight: 700; letter-spacing: 4px; }

.tips {
  font-size: 12px;
  color: var(--text-3);
  text-align: center;
  border-top: 1px dashed #223154;
  padding-top: 12px;
  margin-top: 8px;
  line-height: 2;
}

.badges { display: flex; justify-content: center; gap: 10px; margin-top: 14px; }
</style>

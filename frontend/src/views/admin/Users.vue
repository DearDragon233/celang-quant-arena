<template>
  <el-card shadow="never" class="page-card">
    <div class="table-toolbar">
      <div class="filters">
        <el-input
          v-model="query.keyword"
          placeholder="搜索登录名/昵称"
          clearable
          style="width: 220px"
          @keyup.enter="load(1)"
          @clear="load(1)"
        />
        <el-button type="primary" plain @click="load(1)">查询</el-button>
      </div>
    </div>

    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="nickname" label="昵称" width="110" />
      <el-table-column prop="school" label="学校" width="130" />
      <el-table-column prop="username" label="登录名" width="120" />
      <el-table-column label="可用资金" width="130" align="right">
        <template #default="{ row }">{{ num(row.cash) }}</template>
      </el-table-column>
      <el-table-column label="总资产" width="140" align="right">
        <template #default="{ row }">
          <b>{{ num(row.total) }}</b>
        </template>
      </el-table-column>
      <el-table-column prop="order_count" label="成交笔数" width="100" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'warning'" size="small">
            {{ row.is_active ? '正常' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="注册时间" width="180" />
      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openReset(row)">重置密码</el-button>
          <el-button link :type="row.is_active ? 'warning' : 'success'" @click="toggleActive(row)">
            {{ row.is_active ? '禁用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        v-model:current-page="query.page"
        :page-size="query.size"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="load()"
      />
    </div>
  </el-card>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

const list = ref([])
const total = ref(0)
const loading = ref(false)
const query = reactive({ page: 1, size: 10, keyword: '' })

function num(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function load(page) {
  if (page) query.page = page
  loading.value = true
  try {
    const params = Object.fromEntries(Object.entries(query).filter(([, v]) => v !== ''))
    const data = await api.get('/admin/users', { params })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function openReset(row) {
  const { value } = await ElMessageBox.prompt(`为「${row.nickname}」设置新密码（至少 6 位）`, '重置密码', {
    inputType: 'password',
    inputPattern: /^.{6,}$/,
    inputErrorMessage: '密码至少 6 位',
  })
  await api.put(`/admin/users/${row.id}`, { password: value })
  ElMessage.success('密码已重置')
}

async function toggleActive(row) {
  await api.put(`/admin/users/${row.id}`, { is_active: !row.is_active })
  ElMessage.success(row.is_active ? '已禁用' : '已启用')
  load()
}

onMounted(() => load())
</script>

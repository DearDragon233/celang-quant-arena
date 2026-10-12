<template>
  <el-card shadow="never">
    <template #header>
      <div class="head">
        <div class="panel-title">比赛发布与管理</div>
        <el-button type="primary" :icon="Plus" @click="openCreate">发布新比赛</el-button>
      </div>
    </template>

    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="比赛名称" min-width="200" />
      <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
      <el-table-column label="初始资金" width="120" align="right">
        <template #default="{ row }">{{ Number(row.initial_cash).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column prop="start_date" label="开始" width="160" />
      <el-table-column prop="end_date" label="结束" width="160" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status_text)" size="small">{{ row.status_text }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="entry_count" label="报名" width="70" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button
            link
            :type="row.published ? 'warning' : 'success'"
            @click="toggle(row)"
          >
            {{ row.published ? '下架' : '发布' }}
          </el-button>
          <el-button link type="danger" :disabled="row.entry_count > 0" @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑比赛' : '发布新比赛'" width="540px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="比赛名称" prop="name">
          <el-input v-model="form.name" maxlength="60" placeholder="如 策澜杯 · 秋季模拟盘对决" />
        </el-form-item>
        <el-form-item label="比赛说明" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" maxlength="255" />
        </el-form-item>
        <el-form-item label="初始资金" prop="initial_cash">
          <el-input-number v-model="form.initial_cash" :min="10000" :step="100000" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="开始时间" prop="start_date">
          <el-date-picker v-model="form.start_date" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间" prop="end_date">
          <el-date-picker v-model="form.end_date" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="是否发布">
          <el-switch v-model="form.status" active-value="published" inactive-value="draft"
                     active-text="发布" inactive-text="草稿" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import api from '../../api'

const list = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const formRef = ref()

const form = reactive({
  id: 0, name: '', description: '', initial_cash: 1000000,
  start_date: '', end_date: '', status: 'published',
})
const rules = {
  name: [{ required: true, message: '请输入比赛名称', trigger: 'blur' }],
  start_date: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  end_date: [{ required: true, message: '请选择结束时间', trigger: 'change' }],
}

function statusType(t) {
  return { 进行中: 'success', 未开始: 'primary', 已结束: 'info', 未发布: 'danger' }[t] || 'info'
}

async function load() {
  loading.value = true
  try {
    list.value = await api.get('/admin/contests')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  Object.assign(form, {
    id: 0, name: '', description: '', initial_cash: 1000000,
    start_date: '', end_date: '', status: 'published',
  })
  dialogVisible.value = true
}

function openEdit(row) {
  Object.assign(form, { ...row })
  dialogVisible.value = true
}

async function save() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      await api.put(`/admin/contests/${form.id}`, { ...form })
      ElMessage.success('比赛已更新')
    } else {
      await api.post('/admin/contests', { ...form })
      ElMessage.success('比赛已创建')
    }
    dialogVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

async function toggle(row) {
  const body = {
    name: row.name, description: row.description, initial_cash: row.initial_cash,
    start_date: row.start_date, end_date: row.end_date,
    status: row.published ? 'draft' : 'published',
  }
  await api.put(`/admin/contests/${row.id}`, body)
  ElMessage.success(row.published ? '已下架（选手不可见）' : '已发布')
  load()
}

async function del(row) {
  await ElMessageBox.confirm(`确定删除比赛「${row.name}」吗？`, '删除确认', { type: 'warning' })
  await api.delete(`/admin/contests/${row.id}`)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

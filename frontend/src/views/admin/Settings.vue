<template>
  <el-card shadow="never">
    <template #header><div class="panel-title">大赛赛程设置</div></template>
    <el-form label-width="110px" style="max-width: 520px" v-loading="loading">
      <el-form-item label="大赛名称">
        <el-input v-model="form.comp_name" maxlength="60" />
      </el-form-item>
      <el-form-item label="赛季">
        <el-input v-model="form.comp_season" maxlength="30" placeholder="如 2026 秋季赛" />
      </el-form-item>
      <el-form-item label="开始日期">
        <el-date-picker v-model="form.comp_start" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item label="结束日期">
        <el-date-picker v-model="form.comp_end" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">保存设置</el-button>
      </el-form-item>
    </el-form>
    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="赛程信息展示在用户端「大赛排行」页与登录页，排行榜按总收益率实时排序。"
    />
  </el-card>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const loading = ref(true)
const saving = ref(false)
const form = reactive({ comp_name: '', comp_season: '', comp_start: '', comp_end: '' })

async function load() {
  loading.value = true
  try {
    Object.assign(form, await api.get('/admin/settings'))
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await api.put('/admin/settings', { ...form })
    ElMessage.success('赛程设置已保存')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

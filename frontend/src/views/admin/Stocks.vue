<template>
  <el-card shadow="never" class="page-card">
    <div class="table-toolbar">
      <h3>股票池（{{ list.length }} 只）</h3>
      <span class="tip">停用的股票将不在行情与交易中可见；行情为模拟数据，仅供教学演示。</span>
    </div>

    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="code" label="代码" width="90" />
      <el-table-column prop="name" label="名称" width="110" />
      <el-table-column prop="sector" label="板块" width="100" />
      <el-table-column label="市场" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="row.market === 'CN' ? 'info' : 'warning'" effect="plain">
            {{ row.market === 'CN' ? 'A股' : '美股' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最新价" width="100" align="right">
        <template #default="{ row }">{{ row.price?.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="涨跌幅" width="100" align="right">
        <template #default="{ row }">
          <span :class="row.change_pct > 0 ? 'up' : row.change_pct < 0 ? 'down' : 'flat'" class="num">
            {{ row.change_pct > 0 ? '+' : '' }}{{ row.change_pct }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="bar_count" label="行情条数" width="100" />
      <el-table-column prop="description" label="简介" min-width="200" show-overflow-tooltip />
      <el-table-column label="在市" width="90">
        <template #default="{ row }">
          <el-switch :model-value="row.is_active" @change="toggle(row, $event)" />
        </template>
      </el-table-column>
      <el-table-column label="备注" min-width="180">
        <template #default="{ row }">
          <el-input
            v-model="row.description"
            size="small"
            maxlength="255"
            @change="saveDesc(row)"
          />
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../../api'

const list = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    list.value = await api.get('/admin/stocks')
  } finally {
    loading.value = false
  }
}

async function toggle(row, value) {
  await api.put(`/admin/stocks/${row.id}`, { is_active: value })
  ElMessage.success(value ? '已恢复在市' : '已停牌（对用户隐藏）')
  load()
}

async function saveDesc(row) {
  await api.put(`/admin/stocks/${row.id}`, { description: row.description })
  ElMessage.success('备注已保存')
}

onMounted(load)
</script>

<style scoped>
.tip {
  color: #b0b6c0;
  font-size: 12px;
}
</style>

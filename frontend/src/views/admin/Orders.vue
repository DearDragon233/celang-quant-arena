<template>
  <el-card shadow="never" class="page-card">
    <div class="table-toolbar">
      <div class="filters">
        <el-input
          v-model="query.keyword"
          placeholder="搜索投资者昵称/登录名"
          clearable
          style="width: 210px"
          @keyup.enter="load(1)"
          @clear="load(1)"
        />
        <el-select v-model="query.side" placeholder="全部方向" clearable style="width: 120px" @change="load(1)">
          <el-option label="买入" value="buy" />
          <el-option label="卖出" value="sell" />
        </el-select>
        <el-button type="primary" plain @click="load(1)">查询</el-button>
      </div>
      <span class="sum">累计成交 <b>{{ total }}</b> 笔</span>
    </div>

    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="user" label="投资者" width="110" />
      <el-table-column prop="code" label="代码" width="80" />
      <el-table-column prop="name" label="名称" width="100" />
      <el-table-column label="市场" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="row.market === 'CN' ? 'info' : 'warning'" effect="plain">
            {{ row.market === 'CN' ? 'A股' : '美股' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="方向" width="90">
        <template #default="{ row }">
          <el-tag :type="row.side === 'buy' ? 'danger' : 'success'" size="small" effect="dark">
            {{ row.side === 'buy' ? '买入' : '卖出' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="成交价" width="100" align="right">
        <template #default="{ row }">{{ row.price.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="qty" label="数量" width="90" align="right" />
      <el-table-column label="成交额" width="120" align="right">
        <template #default="{ row }">{{ Number(row.amount).toLocaleString() }}</template>
      </el-table-column>
      <el-table-column label="费用" width="90" align="right">
        <template #default="{ row }">{{ row.fee.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column prop="time" label="成交时间" min-width="170" />
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
import api from '../../api'

const list = ref([])
const total = ref(0)
const loading = ref(false)
const query = reactive({ page: 1, size: 12, side: '', keyword: '' })

async function load(page) {
  if (page) query.page = page
  loading.value = true
  try {
    const params = Object.fromEntries(Object.entries(query).filter(([, v]) => v !== ''))
    const data = await api.get('/admin/orders', { params })
    list.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

onMounted(() => load())
</script>

<style scoped>
.sum {
  color: #5a6070;
  font-size: 13px;
}

.sum b {
  color: #e03131;
}
</style>

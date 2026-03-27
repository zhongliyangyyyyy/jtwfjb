<template>
  <div class="report-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>📋 举报记录列表</span>
          <el-button text @click="fetchReports">
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </template>

      <el-table :data="reports" v-loading="loading" stripe>
        <el-table-column prop="id" label="编号" width="220" show-overflow-tooltip />
        <el-table-column prop="license_plate" label="车牌" width="120">
          <template #default="{ row }">
            <span class="plate">{{ row.license_plate || '未识别' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="violation_type" label="违法类型" width="150">
          <template #default="{ row }">
            {{ formatViolationType(row.violation_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ formatStatus(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="举报时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="200">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="viewDetail(row)">
              查看
            </el-button>
            <el-button
              type="success"
              size="small"
              link
              :disabled="row.status !== 'completed'"
              @click="downloadReport(row)"
            >
              下载报告
            </el-button>
            <el-button type="danger" size="small" link @click="deleteReport(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="举报详情" width="700px">
      <div v-if="currentReport" class="report-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="编号">{{ currentReport.id }}</el-descriptions-item>
          <el-descriptions-item label="车牌">
            <span class="highlight">{{ currentReport.license_plate || '未识别' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="违法类型">
            {{ formatViolationType(currentReport.violation_type) }}
          </el-descriptions-item>
          <el-descriptions-item label="车辆类型">
            {{ currentReport.vehicle_type || '未知' }}
          </el-descriptions-item>
          <el-descriptions-item label="违法地点" :span="2">
            {{ currentReport.violation_location || '未知' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentReport.status)">
              {{ formatStatus(currentReport.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="举报时间">
            {{ formatDate(currentReport.created_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="currentReport.thumbnail_path" class="thumbnail-section">
          <p>视频缩略图：</p>
          <img :src="'/api/v1/reports/' + currentReport.id + '/thumbnail'" alt="缩略图" />
        </div>

        <div v-if="currentReport.violation_image_path" class="violation-image-section">
          <p>违规证据截图：</p>
          <img
            :src="'/api/v1/reports/' + currentReport.id + '/violation-image'"
            alt="违规标注图像"
            class="violation-image"
          />
          <p class="violation-hint">图中标注了检测到的违规行为（车辆边界框、车道线）</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import axios from 'axios'

const reports = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const detailVisible = ref(false)
const currentReport = ref(null)

const fetchReports = async () => {
  loading.value = true
  try {
    const response = await axios.get('/api/v1/reports', {
      params: {
        skip: (currentPage.value - 1) * pageSize.value,
        limit: pageSize.value
      }
    })
    reports.value = response.data.reports || []
    total.value = response.data.total || 0
  } catch (error) {
    console.error('获取列表失败:', error)
    ElMessage.error('获取列表失败')
  } finally {
    loading.value = false
  }
}

const handleSizeChange = (val) => {
  pageSize.value = val
  fetchReports()
}

const handlePageChange = (val) => {
  currentPage.value = val
  fetchReports()
}

const viewDetail = async (row) => {
  try {
    const response = await axios.get(`/api/v1/reports/${row.id}`)
    currentReport.value = response.data
    detailVisible.value = true
  } catch (error) {
    console.error('获取详情失败:', error)
    ElMessage.error('获取详情失败')
  }
}

const downloadReport = async (row) => {
  try {
    const response = await axios.get(`/api/v1/reports/${row.id}/download`, {
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `举报报告_${row.license_plate || row.id}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('报告下载成功')
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败')
  }
}

const deleteReport = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除这条举报记录吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await axios.delete(`/api/v1/reports/${row.id}`)
    ElMessage.success('删除成功')
    fetchReports()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const formatViolationType = (type) => {
  const types = {
    'red_light': '违反信号灯',
    'wrong_way': '逆行',
    'emergency_lane': '占用应急车道',
    'illegal_parking': '违规停放',
    'illegal_change': '违规变道',
    'solid_line_change': '跨实线变道'
  }
  return types[type] || type || '-'
}

const formatStatus = (status) => {
  const statuses = {
    'pending': '待处理',
    'processing': '处理中',
    'completed': '已完成',
    'failed': '失败'
  }
  return statuses[status] || status || '-'
}

const getStatusType = (status) => {
  const types = {
    'pending': 'info',
    'processing': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return types[status] || 'info'
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  fetchReports()
})
</script>

<style scoped>
.report-list {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.plate {
  font-weight: bold;
  color: #e74c3c;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.highlight {
  color: #e74c3c;
  font-weight: bold;
}

.thumbnail-section {
  margin-top: 20px;
}

.thumbnail-section p {
  margin-bottom: 10px;
  color: #666;
}

.thumbnail-section img {
  max-width: 100%;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.violation-image-section {
  margin-top: 20px;
}

.violation-image-section p {
  margin-bottom: 10px;
  color: #666;
}

.violation-image {
  max-width: 100%;
  border: 2px solid #e74c3c;
  border-radius: 4px;
}

.violation-hint {
  color: #888;
  font-size: 12px;
  margin-top: 5px;
}
</style>

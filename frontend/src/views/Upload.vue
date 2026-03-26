<template>
  <div class="upload-view">
    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <span>📤 上传交通违法视频</span>
        </div>
      </template>

      <el-form :model="form" label-width="120px">
        <el-form-item label="违法地点">
          <el-input
            v-model="form.violationLocation"
            placeholder="请输入违法发生地点"
            clearable
          />
        </el-form-item>

        <el-form-item label="视频文件">
          <el-upload
            ref="uploadRef"
            class="video-uploader"
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            accept="video/*"
            drag
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽视频文件到此处，或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 MP4、MOV、AVI 格式，最大 500MB
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="uploading"
            :disabled="!selectedFile"
            @click="handleUpload"
          >
            {{ uploading ? '上传中...' : '开始上传并分析' }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 上传进度 -->
      <div v-if="uploadProgress > 0" class="progress-section">
        <el-progress :percentage="uploadProgress" :stroke-width="20" />
        <p class="progress-text">正在上传: {{ uploadProgress }}%</p>
      </div>
    </el-card>

    <!-- 分析结果 -->
    <el-card v-if="analysisResult" class="result-card">
      <template #header>
        <div class="card-header">
          <span>📋 分析结果</span>
          <el-tag :type="analysisResult.status === 'completed' ? 'success' : 'warning'">
            {{ analysisResult.status === 'completed' ? '分析完成' : '处理中' }}
          </el-tag>
        </div>
      </template>

      <div v-if="analysisResult.status === 'completed'">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="车牌号码">
            <span class="highlight">{{ analysisResult.license_plate || '未能识别' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="车牌置信度">
            {{ analysisResult.plate_confidence ? (analysisResult.plate_confidence * 100).toFixed(1) + '%' : 'N/A' }}
          </el-descriptions-item>
          <el-descriptions-item label="违法类型">
            <span class="highlight">{{ formatViolationType(analysisResult.violation_type) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="车辆类型">
            {{ analysisResult.vehicle_type || '未知' }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="action-buttons">
          <el-button type="primary" @click="downloadReport">
            📄 下载举报报告
          </el-button>
          <el-button @click="resetForm">
            上传新视频
          </el-button>
        </div>
      </div>

      <div v-else class="processing">
        <el-icon class="is-loading" :size="40"><loading /></el-icon>
        <p>正在分析视频，请稍候...</p>
        <p class="tip">此过程可能需要几分钟，请勿关闭页面</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Loading } from '@element-plus/icons-vue'
import axios from 'axios'

const uploadRef = ref(null)
const selectedFile = ref(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const analysisResult = ref(null)
const currentReportId = ref(null)

const form = reactive({
  violationLocation: ''
})

const handleFileChange = (file) => {
  selectedFile.value = file.raw
  uploadProgress.value = 0
  analysisResult.value = null
}

const handleFileRemove = () => {
  selectedFile.value = null
  uploadProgress.value = 0
}

const handleUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请选择视频文件')
    return
  }

  uploading.value = true
  uploadProgress.value = 0
  analysisResult.value = null

  try {
    // 简单上传（直接上传整个文件）
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('violation_location', form.violationLocation)

    const uploadResponse = await axios.post('/api/v1/upload/simple', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          uploadProgress.value = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
        }
      }
    })

    currentReportId.value = uploadResponse.data.report_id
    ElMessage.success('视频上传成功，开始分析...')

    // 触发分析
    await triggerAnalysis()

  } catch (error) {
    console.error('上传失败:', error)
    ElMessage.error('上传失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    uploading.value = false
  }
}

const triggerAnalysis = async () => {
  if (!currentReportId.value) return

  try {
    await axios.post(`/api/v1/reports/${currentReportId.value}/analyze`)

    // 轮询状态
    pollAnalysisStatus()
  } catch (error) {
    console.error('启动分析失败:', error)
    ElMessage.error('启动分析失败')
  }
}

const pollAnalysisStatus = async () => {
  const checkStatus = async () => {
    try {
      const response = await axios.get(`/api/v1/reports/${currentReportId.value}`)
      const report = response.data

      if (report.status === 'completed') {
        analysisResult.value = report
        ElMessage.success('分析完成！')
        return
      } else if (report.status === 'failed') {
        ElMessage.error('分析失败: ' + (report.error_message || '未知错误'))
        return
      }

      // 继续轮询
      setTimeout(checkStatus, 3000)
    } catch (error) {
      console.error('查询状态失败:', error)
    }
  }

  // 启动轮询
  setTimeout(checkStatus, 2000)
}

const downloadReport = async () => {
  if (!currentReportId.value) return

  try {
    const response = await axios.get(
      `/api/v1/reports/${currentReportId.value}/download`,
      { responseType: 'blob' }
    )

    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `举报报告_${currentReportId.value}.pdf`)
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

const resetForm = () => {
  selectedFile.value = null
  uploadProgress.value = 0
  analysisResult.value = null
  currentReportId.value = null
  form.violationLocation = ''
  uploadRef.value?.clearFiles()
}

const formatViolationType = (type) => {
  const types = {
    'red_light': '违反道路交通信号灯',
    'wrong_way': '逆向行驶',
    'emergency_lane': '占用应急车道',
    'illegal_parking': '违规停放',
    'illegal_change': '违规变道'
  }
  return types[type] || type || '未知'
}
</script>

<style scoped>
.upload-view {
  max-width: 800px;
  margin: 0 auto;
}

.upload-card, .result-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.video-uploader {
  width: 100%;
}

.video-uploader .el-upload {
  width: 100%;
}

.video-uploader .el-upload-dragger {
  width: 100%;
  padding: 40px 20px;
}

.progress-section {
  margin-top: 20px;
}

.progress-text {
  text-align: center;
  margin-top: 10px;
  color: #666;
}

.highlight {
  color: #e74c3c;
  font-weight: bold;
  font-size: 16px;
}

.action-buttons {
  margin-top: 20px;
  display: flex;
  gap: 10px;
}

.processing {
  text-align: center;
  padding: 40px 0;
}

.processing p {
  margin-top: 15px;
  color: #666;
}

.processing .tip {
  font-size: 12px;
  color: #999;
}
</style>

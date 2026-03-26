<template>
  <div class="app-container">
    <header class="app-header">
      <h1>🚗 车辆违法举报系统</h1>
    </header>

    <main class="app-main">
      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane label="上传视频" name="upload">
          <UploadView />
        </el-tab-pane>
        <el-tab-pane label="举报列表" name="list">
          <ReportList />
        </el-tab-pane>
      </el-tabs>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import UploadView from './views/Upload.vue'
import ReportList from './views/ReportList.vue'

const activeTab = ref('upload')
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
  background: #f5f7fa;
}

.app-container {
  min-height: 100vh;
}

.app-header {
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  color: white;
  padding: 20px 0;
  text-align: center;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.app-header h1 {
  font-size: 28px;
  font-weight: 600;
}

.app-main {
  max-width: 1200px;
  margin: 30px auto;
  padding: 0 20px;
}
</style>

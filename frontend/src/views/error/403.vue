<template>
  <div class="error-page">
    <div class="error-code">403</div>
    <div class="error-desc">抱歉，您没有权限访问此页面</div>
    <div class="actions">
      <el-button type="primary" @click="goHome">返回首页</el-button>
      <el-button @click="goBack">返回上一页</el-button>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goHome = () => {
  router.push('/')
}

const goBack = () => {
  router.go(-1)
}
</script>

<style lang="scss" scoped>
.error-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background-color: #f5f7fa;
}

.error-code {
  font-size: 160px;
  font-weight: bold;
  color: #E6A23C;
  margin-bottom: 20px;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
}

.error-desc {
  font-size: 24px;
  color: #606266;
  margin-bottom: 30px;
}

.actions {
  display: flex;
  gap: 20px;
}
</style> 
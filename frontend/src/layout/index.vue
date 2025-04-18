<template>
  <div class="app-wrapper">
    <!-- 侧边栏 -->
    <div class="sidebar-container">
      <div class="logo-container">
        <h1 class="logo">教育管理系统</h1>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        class="sidebar-menu"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <sidebar-item v-for="route in routes" :key="route.path" :item="route" :base-path="route.path" />
      </el-menu>
    </div>
    
    <!-- 主要内容区 -->
    <div class="main-container">
      <!-- 顶部导航 -->
      <div class="navbar">
        <div class="left">
          <el-icon class="hamburger" @click="toggleSidebar"><Menu /></el-icon>
          <breadcrumb />
        </div>
        <div class="right">
          <el-dropdown trigger="click">
            <div class="avatar-container">
              <span>{{ username }}</span>
              <el-avatar :size="30" :src="avatar" />
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="toProfile">个人信息</el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
      
      <!-- 路由页面 -->
      <app-main />
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { Menu } from '@element-plus/icons-vue'
import { clearAuth } from '@/utils/permission'
import SidebarItem from './components/SidebarItem.vue'
import Breadcrumb from './components/Breadcrumb.vue'
import AppMain from './components/AppMain.vue'

const router = useRouter()
const route = useRoute()

// 用户信息
const username = ref('管理员')
const avatar = ref('')

// 折叠侧边栏
const isCollapse = ref(false)
const toggleSidebar = () => {
  isCollapse.value = !isCollapse.value
}

// 获取路由
const routes = computed(() => {
  // 过滤掉隐藏的路由
  return router.options.routes.filter(route => {
    return !route.meta?.hidden
  })
})

// 当前激活的菜单
const activeMenu = computed(() => {
  return route.path
})

// 跳转到个人信息页
const toProfile = () => {
  router.push('/settings/profile')
}

// 退出登录
const handleLogout = () => {
  ElMessageBox.confirm('确定要退出登录吗?', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    clearAuth()
    router.push('/login')
  }).catch(() => {})
}
</script>

<style lang="scss" scoped>
.app-wrapper {
  display: flex;
  height: 100vh;
  width: 100%;
}

.sidebar-container {
  width: 210px;
  height: 100%;
  background-color: #304156;
  transition: width 0.28s;
  overflow-y: auto;
  
  .logo-container {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    
    .logo {
      color: #fff;
      font-size: 18px;
      margin: 0;
    }
  }
  
  .sidebar-menu {
    border-right: none;
  }
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  
  .navbar {
    height: 50px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 15px;
    box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
    
    .left, .right {
      display: flex;
      align-items: center;
    }
    
    .hamburger {
      margin-right: 15px;
      font-size: 20px;
      cursor: pointer;
    }
    
    .avatar-container {
      display: flex;
      align-items: center;
      cursor: pointer;
      
      span {
        margin-right: 8px;
      }
    }
  }
}
</style> 
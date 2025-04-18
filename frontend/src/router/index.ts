import { createRouter, createWebHistory, RouteRecordRaw, NavigationGuardNext, RouteLocationNormalized } from 'vue-router'
import { UserRole } from '@/types/api'
import { isLoggedIn, getUserRole, clearAuth } from '@/utils/permission'
import { ElMessage } from 'element-plus'

// 基础路由表，所有用户都可以访问
export const constantRoutes: Array<RouteRecordRaw> = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', hidden: true }
  },
  {
    path: '/404',
    name: '404',
    component: () => import('@/views/error/404.vue'),
    meta: { title: '404', hidden: true }
  },
  {
    path: '/403',
    name: '403',
    component: () => import('@/views/error/403.vue'),
    meta: { title: '403', hidden: true }
  }
]

// 需要根据权限动态加载的路由
export const asyncRoutes: Array<RouteRecordRaw> = [
  {
    path: '/',
    component: () => import('@/layout/index.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '仪表盘', icon: 'dashboard', roles: [UserRole.ADMIN, UserRole.HEADTEACHER, UserRole.TEACHER, UserRole.STUDENT] }
      }
    ]
  },
  {
    path: '/user',
    component: () => import('@/layout/index.vue'),
    redirect: '/user/list',
    meta: { title: '用户管理', icon: 'user', roles: [UserRole.ADMIN] },
    children: [
      {
        path: 'list',
        name: 'UserList',
        component: () => import('@/views/user/list.vue'),
        meta: { title: '用户列表', icon: 'list', roles: [UserRole.ADMIN] }
      },
      {
        path: 'create',
        name: 'UserCreate',
        component: () => import('@/views/user/create.vue'),
        meta: { title: '创建用户', icon: 'add', roles: [UserRole.ADMIN] }
      },
      {
        path: 'edit/:id',
        name: 'UserEdit',
        component: () => import('@/views/user/edit.vue'),
        meta: { title: '编辑用户', hidden: true, roles: [UserRole.ADMIN] }
      }
    ]
  },
  {
    path: '/score',
    component: () => import('@/layout/index.vue'),
    redirect: '/score/list',
    meta: { title: '成绩管理', icon: 'score', roles: [UserRole.ADMIN, UserRole.HEADTEACHER, UserRole.TEACHER] },
    children: [
      {
        path: 'list',
        name: 'ScoreList',
        component: () => import('@/views/score/list.vue'),
        meta: { title: '成绩列表', icon: 'list', roles: [UserRole.ADMIN, UserRole.HEADTEACHER, UserRole.TEACHER] }
      },
      {
        path: 'create',
        name: 'ScoreCreate',
        component: () => import('@/views/score/create.vue'),
        meta: { title: '添加成绩', icon: 'add', roles: [UserRole.ADMIN, UserRole.HEADTEACHER, UserRole.TEACHER] }
      },
      {
        path: 'edit/:id',
        name: 'ScoreEdit',
        component: () => import('@/views/score/edit.vue'),
        meta: { title: '编辑成绩', hidden: true, roles: [UserRole.ADMIN, UserRole.HEADTEACHER, UserRole.TEACHER] }
      }
    ]
  },
  {
    path: '/analysis',
    component: () => import('@/layout/index.vue'),
    redirect: '/analysis/list',
    meta: { title: '分析报告', icon: 'chart', roles: [UserRole.ADMIN, UserRole.HEADTEACHER, UserRole.TEACHER] },
    children: [
      {
        path: 'list',
        name: 'AnalysisList',
        component: () => import('@/views/analysis/list.vue'),
        meta: { title: '报告列表', icon: 'list', roles: [UserRole.ADMIN, UserRole.HEADTEACHER, UserRole.TEACHER] }
      },
      {
        path: 'create',
        name: 'AnalysisCreate',
        component: () => import('@/views/analysis/create.vue'),
        meta: { title: '创建报告', icon: 'add', roles: [UserRole.ADMIN, UserRole.HEADTEACHER, UserRole.TEACHER] }
      },
      {
        path: 'view/:id',
        name: 'AnalysisView',
        component: () => import('@/views/analysis/view.vue'),
        meta: { title: '查看报告', hidden: true, roles: [UserRole.ADMIN, UserRole.HEADTEACHER, UserRole.TEACHER] }
      }
    ]
  },
  {
    path: '/settings',
    component: () => import('@/layout/index.vue'),
    redirect: '/settings/profile',
    meta: { title: '系统设置', icon: 'setting', roles: [UserRole.ADMIN] },
    children: [
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/settings/profile.vue'),
        meta: { title: '个人信息', icon: 'user', roles: [UserRole.ADMIN, UserRole.HEADTEACHER, UserRole.TEACHER, UserRole.STUDENT] }
      },
      {
        path: 'system',
        name: 'System',
        component: () => import('@/views/settings/system.vue'),
        meta: { title: '系统设置', icon: 'setting', roles: [UserRole.ADMIN] }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/404',
    meta: { hidden: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes: constantRoutes // 初始只加载基础路由
})

// 根据用户角色动态添加路由
export function generateRoutes() {
  const role = getUserRole()
  const accessedRoutes = filterAsyncRoutes(asyncRoutes, role)
  accessedRoutes.forEach(route => {
    router.addRoute(route)
  })
  return accessedRoutes
}

// 根据用户角色过滤路由
function filterAsyncRoutes(routes: RouteRecordRaw[], role: UserRole): RouteRecordRaw[] {
  const res: RouteRecordRaw[] = []

  routes.forEach(route => {
    const tmp = { ...route }
    if (hasPermission(tmp, role)) {
      if (tmp.children) {
        tmp.children = filterAsyncRoutes(tmp.children, role)
      }
      res.push(tmp)
    }
  })

  return res
}

// 检查路由是否有权限
function hasPermission(route: RouteRecordRaw, role: UserRole): boolean {
  if (route.meta && route.meta.roles) {
    return (route.meta.roles as UserRole[]).includes(role)
  } else {
    return true
  }
}

// 全局前置守卫
router.beforeEach(async (to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - 教育管理系统` : '教育管理系统'

  // 检查是否已登录
  if (isLoggedIn()) {
    if (to.path === '/login') {
      // 已登录情况下访问登录页，重定向到首页
      next({ path: '/' })
    } else {
      // 检查路由是否已添加
      const hasRoutes = router.hasRoute('Dashboard')
      if (hasRoutes) {
        next()
      } else {
        try {
          // 动态添加路由
          generateRoutes()
          // 重新跳转（确保动态添加的路由已加载）
          next({ ...to, replace: true })
        } catch (error) {
          // 发生错误，清除认证信息并跳转到登录页
          clearAuth()
          ElMessage.error('路由获取失败，请重新登录')
          next(`/login?redirect=${to.path}`)
        }
      }
    }
  } else {
    // 未登录情况下，允许访问白名单页面
    if (['/login', '/404', '/403'].includes(to.path)) {
      next()
    } else {
      // 重定向到登录页，并带上目标URL
      next(`/login?redirect=${to.path}`)
    }
  }
})

export default router 
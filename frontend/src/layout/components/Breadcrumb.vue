<template>
  <el-breadcrumb class="app-breadcrumb" separator="/">
    <el-breadcrumb-item v-for="(item, index) in breadcrumbs" :key="item.path">
      <span v-if="index === breadcrumbs.length - 1 || !item.redirect" class="no-redirect">
        {{ item.meta?.title }}
      </span>
      <a v-else @click.prevent="handleLink(item)">{{ item.meta?.title }}</a>
    </el-breadcrumb-item>
  </el-breadcrumb>
</template>

<script lang="ts" setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter, RouteLocationMatched } from 'vue-router'

const route = useRoute()
const router = useRouter()

const breadcrumbs = ref<RouteLocationMatched[]>([])

// 生成面包屑
const getBreadcrumb = () => {
  // 过滤掉隐藏的路由
  let matched = route.matched.filter(item => {
    return !item.meta?.hidden
  })

  // 如果第一个路由不是首页，则加入首页
  if (matched[0]?.path !== '/dashboard') {
    const homePage = {
      path: '/dashboard',
      meta: { title: '首页' },
      redirect: ''
    } as RouteLocationMatched
    matched = [homePage, ...matched]
  }

  breadcrumbs.value = matched
}

// 路由跳转
const handleLink = (item: RouteLocationMatched) => {
  const { redirect, path } = item
  if (redirect) {
    router.push(redirect.toString())
    return
  }
  router.push(path)
}

// 初始化面包屑
getBreadcrumb()

// 监听路由变化
watch(
  () => route.path,
  () => getBreadcrumb()
)
</script>

<style lang="scss" scoped>
.app-breadcrumb {
  display: inline-block;
  font-size: 14px;
  line-height: 50px;
  margin-left: 8px;

  .no-redirect {
    color: #97a8be;
    cursor: text;
  }
}
</style> 
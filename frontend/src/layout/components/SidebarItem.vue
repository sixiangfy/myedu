<template>
  <div v-if="!item.meta || !item.meta.hidden">
    <!-- 有子菜单的情况 -->
    <template v-if="hasOneShowingChild(item.children, item)">
      <app-link v-if="onlyOneChild.meta" :to="resolvePath(onlyOneChild.path)">
        <el-menu-item :index="resolvePath(onlyOneChild.path)">
          <el-icon v-if="onlyOneChild.meta.icon">
            <component :is="onlyOneChild.meta.icon" />
          </el-icon>
          <template #title>{{ onlyOneChild.meta.title }}</template>
        </el-menu-item>
      </app-link>
    </template>
    
    <!-- 没有子菜单的情况 -->
    <el-sub-menu v-else ref="subMenu" :index="resolvePath(item.path)">
      <template #title>
        <el-icon v-if="item.meta.icon">
          <component :is="item.meta.icon" />
        </el-icon>
        <span>{{ item.meta.title }}</span>
      </template>
      
      <sidebar-item
        v-for="child in item.children"
        :key="child.path"
        :item="child"
        :base-path="resolvePath(child.path)"
      />
    </el-sub-menu>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue'
import { RouteRecordRaw } from 'vue-router'
import { isExternal } from '@/utils/validate'
import AppLink from './Link.vue'

// 定义props
const props = defineProps({
  item: {
    type: Object as () => RouteRecordRaw,
    required: true
  },
  basePath: {
    type: String,
    required: true
  }
})

// 唯一子菜单
const onlyOneChild = ref<any>(null)

// 判断是否有一个显示的子菜单
const hasOneShowingChild = (children: RouteRecordRaw[] = [], parent: RouteRecordRaw) => {
  // 过滤出显示的子菜单
  const showingChildren = children.filter(item => {
    if (item.meta?.hidden) {
      return false
    } else {
      // 设置为唯一子菜单
      onlyOneChild.value = item
      return true
    }
  })

  // 当只有一个子菜单时直接显示
  if (showingChildren.length === 1) {
    return true
  }

  // 如果没有子菜单，则把父菜单作为唯一子菜单
  if (showingChildren.length === 0) {
    onlyOneChild.value = { ...parent, path: '', noShowingChildren: true }
    return true
  }

  return false
}

// 解析路径
const resolvePath = (routePath: string) => {
  if (isExternal(routePath)) {
    return routePath
  }
  if (isExternal(props.basePath)) {
    return props.basePath
  }
  return props.basePath + '/' + routePath
}
</script> 
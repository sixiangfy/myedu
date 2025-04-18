<template>
  <div class="score-edit-container">
    <div class="header">
      <h2>编辑成绩</h2>
      <el-button @click="$router.push('/score/list')">返回列表</el-button>
    </div>
    
    <el-card class="form-card" v-loading="loading">
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
        status-icon
      >
        <el-form-item label="考试" prop="exam_id">
          <el-select v-model="formData.exam_id" placeholder="请选择考试" filterable>
            <el-option
              v-for="item in examOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="科目" prop="subject_id">
          <el-select v-model="formData.subject_id" placeholder="请选择科目" filterable>
            <el-option
              v-for="item in subjectOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="班级" prop="class_id" v-if="!isReadOnly">
          <el-select 
            v-model="formData.class_id" 
            placeholder="请选择班级" 
            filterable 
            @change="handleClassChange"
          >
            <el-option
              v-for="item in classOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="学生" prop="student_id">
          <el-select 
            v-model="formData.student_id" 
            placeholder="请选择学生" 
            filterable
            :disabled="isReadOnly || !formData.class_id"
          >
            <el-option
              v-for="item in studentOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="分数" prop="score">
          <el-input-number 
            v-model="formData.score" 
            :min="0" 
            :max="100" 
            :precision="1"
            :step="0.5"
            style="width: 160px"
          />
        </el-form-item>
        
        <el-form-item label="排名" prop="ranking">
          <el-input-number 
            v-model="formData.ranking" 
            :min="1"
            :step="1"
            :precision="0"
            style="width: 160px"
          />
        </el-form-item>
        
        <el-form-item label="备注" prop="comments">
          <el-input 
            v-model="formData.comments" 
            type="textarea" 
            :rows="3" 
            placeholder="请输入备注信息"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">保存</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { UpdateScoreParams } from '@/types/api'
import { getScore, updateScore } from '@/api/score'
import { getExams, getSubjects, getClasses, getStudentsByClass } from '@/api/common'

// 路由
const route = useRoute()
const router = useRouter()

// 获取成绩ID
const scoreId = computed(() => Number(route.params.id))

// 表单引用
const formRef = ref<FormInstance>()

// 加载状态
const loading = ref(false)
const submitting = ref(false)
const isReadOnly = ref(false)

// 下拉选项
const examOptions = ref<{ value: number; label: string }[]>([])
const subjectOptions = ref<{ value: number; label: string }[]>([])
const classOptions = ref<{ value: number; label: string }[]>([])
const studentOptions = ref<{ value: number; label: string }[]>([])

// 表单数据
const formData = reactive<UpdateScoreParams & { class_id?: number }>({
  exam_id: undefined,
  subject_id: undefined,
  student_id: undefined,
  score: 0,
  ranking: undefined,
  comments: '',
  class_id: undefined
})

// 表单验证规则
const formRules = reactive<FormRules>({
  exam_id: [
    { required: true, message: '请选择考试', trigger: 'change' }
  ],
  subject_id: [
    { required: true, message: '请选择科目', trigger: 'change' }
  ],
  student_id: [
    { required: true, message: '请选择学生', trigger: 'change' }
  ],
  score: [
    { required: true, message: '请输入分数', trigger: 'blur' },
    { type: 'number', min: 0, max: 100, message: '分数范围为0-100', trigger: 'blur' }
  ]
})

// 获取下拉选项数据
const fetchOptions = async () => {
  try {
    loading.value = true
    
    // 获取考试列表
    const exams = await getExams()
    examOptions.value = exams.map(exam => ({
      value: exam.id,
      label: exam.name
    }))
    
    // 获取科目列表
    const subjects = await getSubjects()
    subjectOptions.value = subjects.map(subject => ({
      value: subject.id,
      label: subject.name
    }))
    
    // 获取班级列表
    const classes = await getClasses()
    classOptions.value = classes.map(cls => ({
      value: cls.id,
      label: cls.name
    }))
  } catch (error) {
    console.error('获取选项数据失败', error)
    ElMessage.error('获取选项数据失败')
  } finally {
    loading.value = false
  }
}

// 班级变更处理
const handleClassChange = async (classId: number) => {
  if (!classId) {
    studentOptions.value = []
    formData.student_id = undefined
    return
  }
  
  try {
    loading.value = true
    
    // 根据班级获取学生列表
    const students = await getStudentsByClass(classId)
    studentOptions.value = students.map(student => ({
      value: student.id,
      label: student.name
    }))
    
    // 如果不是编辑模式，重置学生选择
    if (!isReadOnly.value) {
      formData.student_id = undefined
    }
  } catch (error) {
    console.error('获取班级学生失败', error)
    ElMessage.error('获取班级学生失败')
  } finally {
    loading.value = false
  }
}

// 加载成绩数据
const loadScoreData = async () => {
  if (!scoreId.value) return
  
  try {
    loading.value = true
    const scoreData = await getScore(scoreId.value)
    
    if (scoreData) {
      // 填充表单数据
      formData.exam_id = scoreData.exam_id
      formData.subject_id = scoreData.subject_id
      formData.student_id = scoreData.student_id
      formData.score = scoreData.score
      formData.ranking = scoreData.ranking
      formData.comments = scoreData.comments || ''
      formData.class_id = scoreData.class_id // 学生所在的班级ID
      
      // 标记为只读模式（学生不可更改）
      isReadOnly.value = true
      
      // 加载该学生所在班级的学生列表
      if (formData.class_id) {
        await handleClassChange(formData.class_id)
      }
    } else {
      ElMessage.error('成绩数据不存在')
      router.push('/score/list')
    }
  } catch (error) {
    console.error('获取成绩数据失败', error)
    ElMessage.error('获取成绩数据失败')
    router.push('/score/list')
  } finally {
    loading.value = false
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value || !scoreId.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        submitting.value = true
        
        // 创建更新数据对象
        const updateData: UpdateScoreParams = {
          score: formData.score,
          ranking: formData.ranking,
          comments: formData.comments
        }
        
        await updateScore(scoreId.value, updateData)
        ElMessage.success('更新成绩成功')
        router.push('/score/list')
      } catch (error: any) {
        console.error('更新成绩失败', error)
        ElMessage.error(error.message || '更新成绩失败')
      } finally {
        submitting.value = false
      }
    }
  })
}

// 重置表单
const resetForm = () => {
  loadScoreData() // 重新加载原始数据
}

// 组件挂载时获取数据
onMounted(async () => {
  await fetchOptions()
  await loadScoreData()
})
</script>

<style lang="scss" scoped>
.score-edit-container {
  padding: 20px;
  
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    h2 {
      margin: 0;
    }
  }
  
  .form-card {
    max-width: 800px;
  }
}
</style> 
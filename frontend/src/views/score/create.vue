<template>
  <div class="score-create-container">
    <div class="header">
      <h2>添加成绩</h2>
      <el-button @click="$router.push('/score/list')">返回列表</el-button>
    </div>
    
    <el-card class="form-card">
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
        
        <el-form-item label="班级" prop="class_id">
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
            :disabled="!formData.class_id"
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
          <el-button type="primary" @click="handleSubmit" :loading="loading">提交</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { CreateScoreParams } from '@/types/api'
import { createScore } from '@/api/score'
import { getExams, getSubjects, getClasses, getStudentsByClass } from '@/api/common'

// 路由
const router = useRouter()

// 表单引用
const formRef = ref<FormInstance>()

// 加载状态
const loading = ref(false)

// 下拉选项
const examOptions = ref<{ value: number; label: string }[]>([])
const subjectOptions = ref<{ value: number; label: string }[]>([])
const classOptions = ref<{ value: number; label: string }[]>([])
const studentOptions = ref<{ value: number; label: string }[]>([])

// 表单数据
const formData = reactive<CreateScoreParams & { class_id?: number }>({
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
  ],
  ranking: [
    { type: 'number', min: 1, message: '排名必须大于0', trigger: 'blur' }
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
    
    // 重置学生选择
    formData.student_id = undefined
  } catch (error) {
    console.error('获取班级学生失败', error)
    ElMessage.error('获取班级学生失败')
  } finally {
    loading.value = false
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        loading.value = true
        
        // 构建提交数据，移除class_id（API不需要）
        const submitData = { ...formData }
        delete submitData.class_id
        
        await createScore(submitData)
        ElMessage.success('添加成绩成功')
        router.push('/score/list')
      } catch (error: any) {
        console.error('添加成绩失败', error)
        ElMessage.error(error.message || '添加成绩失败')
      } finally {
        loading.value = false
      }
    }
  })
}

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  
  // 清空学生列表
  studentOptions.value = []
}

// 组件挂载时获取选项数据
onMounted(() => {
  fetchOptions()
})
</script>

<style lang="scss" scoped>
.score-create-container {
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
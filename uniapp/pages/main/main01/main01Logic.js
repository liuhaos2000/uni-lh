import { ref } from 'vue'
import { getFormInitData } from '@/services/main/main01'

/**
 * 表单状态和方法的组合式函数（页面内，重命名为 main01Logic）
 */
export function useFormData() {
  // 表单数据
  const formData = ref({
    switch: false,
    radio: 'r1',
    checkbox: [],
    slider: 0,
    input: ''
  })

  // 加载表单数据
  const loadFormData = async (option) => {
    try {
      uni.showLoading({ title: '加载中...' })

      // 获取初始数据
      const initData = await getFormInitData()

      // 设置表单数据
      formData.value = {
        ...formData.value,  // 保留默认值
        ...initData         // 使用获取到的数据覆盖 
      }

      // 处理预设值
      if (option?.preset) {
        try {
          const preset = JSON.parse(option.preset)
          formData.value = {
            ...formData.value,
            ...preset
          }
        } catch (e) {
          console.error('预设数据解析失败：', e)
        }
      }

      console.log('表单数据已加载：', formData.value)

    } catch (error) {
      uni.showToast({
        title: '加载数据失败',
        icon: 'none',
        duration: 2000
      })
      console.error('加载数据失败：', error)
    } finally {
      uni.hideLoading()
    }
  }

  // 表单重置
  const resetForm = () => {
    formData.value = {
      switch: false,
      radio: '',
      checkbox: [],
      slider: 0,
      input: ''
    }
  }

  // 表单提交
  const submitForm = (formdata) => {
    console.log('表单提交数据：', formdata)
    uni.showModal({
      content: '表单数据内容：' + JSON.stringify(formdata),
      showCancel: false
    })
  }

  // 表单字段更新方法
  const updateFormField = (field, value) => {
    formData.value[field] = value
  }

  return {
    formData,
    loadFormData,
    resetForm,
    submitForm,
    updateFormField
  }
}
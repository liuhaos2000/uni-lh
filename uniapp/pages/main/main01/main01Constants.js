/**
 * 页面级表单相关常量（已重命名为 main01Constants）
 */
export const FORM_DEFAULTS = {
  // 表单默认值
  DEFAULT_VALUES: {
    switch: false,
    radio: 'r1',
    checkbox: [],
    slider: 0,
    input: ''
  },
  
  // 单选选项
  RADIO_OPTIONS: [
    { value: 'r1', label: '选项一' },
    { value: 'r2', label: '选项二' }
  ],
  
  // 复选框选项
  CHECKBOX_OPTIONS: [
    { value: 'c1', label: '选项一' },
    { value: 'c2', label: '选项二' }
  ]
}
/**
 * 全局环境配置
 */
export default {
  // 全局mock开关
  USE_MOCK: false,
  
  // API配置
  API: {
    // API基础URL
    BASE_URL: 'http://localhost:8000/api',
    
    // 超时时间（毫秒）
    TIMEOUT: 10000,
    
    // API版本
    VERSION: 'v1'
  },
  
  // 各模块mock配置
  MOCK: {
    // 是否启用延迟模拟（毫秒，设为0则不延迟）
    DELAY: 500
  }
}
// API配置文件
const isDevelopment = import.meta.env.MODE === 'development'

// 后端服务地址配置
export const API_CONFIG = {
  // Flask后端地址
  BASE_URL: isDevelopment ? 'http://localhost:5000' : '',
  
  // Socket.IO配置
  SOCKET_CONFIG: {
    transports: ['websocket', 'polling'],
    timeout: 10000,
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 2000,
    // 开发环境需要指定后端地址
    ...(isDevelopment ? {
      forceNew: true,
      // 连接到Flask后端
      url: 'http://localhost:5000'
    } : {})
  },
  
  // 视频流端点
  VIDEO_STREAM: {
    getUrl: (cameraId) => `${API_CONFIG.BASE_URL}/video_feed/${cameraId}`
  }
}

// API端点
export const API_ENDPOINTS = {
  // 视频流
  VIDEO_FEED: '/video_feed',
  
  // 如果需要其他API端点，可以在这里添加
  // SYSTEM_STATUS: '/api/system/status',
  // CAMERA_LIST: '/api/cameras',
}

export default API_CONFIG 
// API配置文件
const isDevelopment = import.meta.env.MODE === 'development'

// 后端服务地址配置
export const API_CONFIG = {
  // Flask后端地址
  BASE_URL: isDevelopment ? 'http://127.0.0.1:5000' : '',
  
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
      url: 'http://127.0.0.1:5000'
    } : {})
  },
  
  // 视频流端点
  VIDEO_STREAM: {
    getUrl: (cameraId) => `${API_CONFIG.BASE_URL}/video_feed/${cameraId}`
  },
  
  // 设备管理端点
  DEVICE_MANAGEMENT: {
    getDevices: () => `${API_CONFIG.BASE_URL}/api/devices`,
    getDeviceStatus: (deviceId) => `${API_CONFIG.BASE_URL}/api/devices/${deviceId}/status`,
    refreshDevices: () => `${API_CONFIG.BASE_URL}/api/devices/refresh`
  }
}

// API端点
export const API_ENDPOINTS = {
  // 视频流
  VIDEO_FEED: '/video_feed',
  
  // 设备管理
  DEVICES: '/api/devices',
  DEVICE_STATUS: '/api/devices/:id/status',
  
  // 如果需要其他API端点，可以在这里添加
  // SYSTEM_STATUS: '/api/system/status',
}

export default API_CONFIG 
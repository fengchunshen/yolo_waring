<template>
  <div id="app">
    <HeaderComponent 
      :current-time="currentTime"
      :connection-status="connectionStatus"
    />
    <div class="main-container">
      <AlertPanel 
        :alerts="alerts"
      />
      <VideoDisplay 
        :cameras="cameras"
        :active-cameras="activeCameras"
        @toggle-camera="toggleCamera"
        @refresh-devices="handleRefreshDevices"
      />
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import io from 'socket.io-client'
import HeaderComponent from './components/HeaderComponent.vue'
import AlertPanel from './components/AlertPanel.vue'
import VideoDisplay from './components/VideoDisplay.vue'
import { API_CONFIG } from './config/api.js'

export default {
  name: 'App',
  components: {
    HeaderComponent,
    AlertPanel,
    VideoDisplay
  },
  setup() {
    const currentTime = ref('')
    const connectionStatus = ref({ status: 'connected', message: '系统运行正常' })
    const alerts = ref([])
    const activeCameras = ref([]) // 动态激活的摄像头
    
    const cameras = ref([]) // 从后端动态获取的摄像头列表

    let socket = null
    let timeInterval = null

    const updateTime = () => {
      const now = new Date()
      currentTime.value = now.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      }).replaceAll('/', '-')
    }

    // 从后端获取设备列表
    const loadDevices = async () => {
      try {
        const response = await fetch(API_CONFIG.DEVICE_MANAGEMENT.getDevices())
        if (response.ok) {
          const result = await response.json()
          if (result.code === 200) {
            // 处理分组数据，转换为扁平化的设备列表
            const allDevices = []
            
            // 检查数据是否为空
            if (result.data && typeof result.data === 'object' && Object.keys(result.data).length > 0) {
              // 遍历分组数据
              Object.entries(result.data).forEach(([groupName, devices]) => {
                if (Array.isArray(devices)) {
                  devices.forEach(device => {
                    allDevices.push({
                      id: parseInt(device.id), // 确保ID是数字类型
                      name: device.name,
                      active: false, // 默认不激活
                      rtspUrl: device.rtspUrl,
                      status: device.status,
                      groupName: groupName, // 添加分组信息
                      ip: device.ip,
                      type: device.type,
                      userName: device.userName,
                      facilityName: device.facilityName
                    })
                  })
                }
              })
            }
            
            cameras.value = allDevices
            
            // 如果有设备，默认激活第一个
            if (cameras.value.length > 0) {
              cameras.value[0].active = true
              activeCameras.value = [cameras.value[0].id]
            }
            
            console.log(`成功加载 ${cameras.value.length} 个设备，分为 ${result.data ? Object.keys(result.data).length : 0} 个分组`)
            console.log('设备列表:', cameras.value)
            console.log('激活的设备:', activeCameras.value)
          } else {
            console.error('获取设备列表失败:', result.message)
          }
        } else {
          console.error('获取设备列表请求失败:', response.status)
        }
      } catch (error) {
        console.error('获取设备列表时发生错误:', error)
        // 如果获取失败，使用默认设备列表作为备用
        cameras.value = [
          { id: 0, name: '默认设备', active: true, rtspUrl: '', status: 'inactive', groupName: '未分配摄像头' }
        ]
        activeCameras.value = [0]
      }
    }

    const connectWebSocket = () => {
      try {
        // 使用配置文件中的Socket.IO配置
        socket = io(API_CONFIG.SOCKET_CONFIG.url || window.location.origin, API_CONFIG.SOCKET_CONFIG)

        socket.on('connect', () => {
          console.log('WebSocket连接成功')
          connectionStatus.value = { status: 'connected', message: '系统运行正常' }
        })

        socket.on('disconnect', () => {
          console.log('WebSocket连接断开')
          connectionStatus.value = { status: 'disconnected', message: '连接断开，正在重连...' }
        })

        socket.on('connect_error', (error) => {
          console.error('WebSocket连接错误:', error)
          connectionStatus.value = { status: 'error', message: '连接错误' }
        })

        socket.on('reconnect', (attemptNumber) => {
          console.log(`WebSocket重连成功，尝试次数: ${attemptNumber}`)
          connectionStatus.value = { status: 'connected', message: '系统运行正常' }
        })

        socket.on('reconnect_failed', () => {
          console.error('WebSocket重连失败')
          connectionStatus.value = { status: 'error', message: '连接失败，请刷新页面' }
        })

        socket.on('intrusion_alert', (data) => {
          console.log('收到告警信息:', data)
          addAlert(data)
        })

        socket.on('system_status', (data) => {
          console.log('收到系统状态:', data)
          if (data.status === 'alert_sent') {
            connectionStatus.value = { status: 'alert', message: data.message }
            setTimeout(() => {
              connectionStatus.value = { status: 'connected', message: '系统运行正常' }
            }, 3000)
          }
        })

      } catch (error) {
        console.error('创建WebSocket连接失败:', error)
        connectionStatus.value = { status: 'error', message: '连接失败' }
      }
    }

    const addAlert = (data) => {
      // 根据设备ID获取设备名称，确保ID类型匹配
      const deviceId = parseInt(data.deviceId)
      const device = cameras.value.find(c => c.id === deviceId)
      const location = device ? device.name : '未知位置'

      const alert = {
        id: Date.now(),
        location: location,
        confidence: data.confidence !== -1 ? (data.confidence * 100).toFixed(1) : '95.0',
        personId: data.person_id,
        duration: data.time_since_first ? Math.round(data.time_since_first) : 0,
        timestamp: data.timestamp,
        isNew: true
      }

      alerts.value.unshift(alert)
      
      // 播放声音提示
      try {
        const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT')
        audio.volume = 0.3
        audio.play().catch(e => console.log('无法播放声音提示:', e))
      } catch (e) {
        console.log('浏览器不支持音频播放')
      }

      // 移除新告警标记
      setTimeout(() => {
        const alertIndex = alerts.value.findIndex(a => a.id === alert.id)
        if (alertIndex !== -1) {
          alerts.value[alertIndex].isNew = false
        }
      }, 500)

      // 限制告警数量
      if (alerts.value.length > 20) {
        alerts.value.pop()
      }
    }

    const toggleCamera = (cameraId) => {
      // 确保cameraId是数字类型
      const id = parseInt(cameraId)
      const camera = cameras.value.find(c => c.id === id)
      console.log('切换摄像头:', { cameraId, id, camera, activeCameras: activeCameras.value })
      if (camera) {
        camera.active = !camera.active
        if (camera.active) {
          activeCameras.value.push(id)
        } else {
          activeCameras.value = activeCameras.value.filter(activeId => activeId !== id)
        }
        console.log('切换后状态:', { camera: camera.active, activeCameras: activeCameras.value })
      }
    }

    // 处理刷新设备列表
    const handleRefreshDevices = async () => {
      try {
        console.log('开始刷新设备列表...')
        
        // 调用后端刷新接口
        const response = await fetch(API_CONFIG.DEVICE_MANAGEMENT.refreshDevices(), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        })
        
        if (response.ok) {
          const result = await response.json()
          if (result.code === 200) {
            console.log('后端刷新成功:', result.message)
            // 重新加载设备列表
            await loadDevices()
            console.log('前端设备列表更新完成')
          } else {
            console.error('后端刷新失败:', result.message)
          }
        } else {
          console.error('刷新请求失败:', response.status)
        }
      } catch (error) {
        console.error('刷新设备列表时发生错误:', error)
      }
    }

    onMounted(async () => {
      updateTime()
      timeInterval = setInterval(updateTime, 1000)
      
      // 先加载设备列表，再连接WebSocket
      await loadDevices()
      connectWebSocket()
    })

    onUnmounted(() => {
      if (timeInterval) {
        clearInterval(timeInterval)
      }
      if (socket) {
        socket.disconnect()
      }
    })

    return {
      currentTime,
      connectionStatus,
      alerts,
      cameras,
      activeCameras,
      toggleCamera,
      handleRefreshDevices
    }
  }
}
</script>

<style>
/* CSS 变量定义 - 2025 辉光玻璃感主题 */
:root {
  --bg-color-dark: #0a0e17;
  --bg-glow-aurora: radial-gradient(ellipse at top, rgba(59, 130, 246, 0.15), transparent 60%), 
                     radial-gradient(ellipse at bottom, rgba(34, 197, 94, 0.1), transparent 70%);
  
  --glass-bg: rgba(18, 24, 40, 0.6);
  --glass-border-color: rgba(59, 130, 246, 0.2);
  --glass-hover-bg: rgba(30, 41, 59, 0.7);
  --glass-blur: 12px;

  --font-color: #e2e8f0;
  --font-color-secondary: #94a3b8;

  --primary-color: #3b82f6;
  --primary-glow-color: rgba(59, 130, 246, 0.6);

  --danger-color: #f43f5e;
  --danger-glow-color: rgba(244, 63, 94, 0.5);
  
  --success-color: #22c55e;
  --success-glow-color: rgba(34, 197, 94, 0.6);

  --border-color: #334155;
  --base-transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body, html {
  height: 100%;
  font-family: 'Microsoft YaHei', 'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  background-color: var(--bg-color-dark);
  background-image: var(--bg-glow-aurora);
  background-attachment: fixed;
  color: var(--font-color);
  font-size: 14px;
  overflow: hidden;
}

#app {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.main-container {
  display: flex;
  flex-grow: 1;
  overflow: hidden;
}

@keyframes pulse-success {
  0% { box-shadow: 0 0 0 0 var(--success-glow-color); }
  70% { box-shadow: 0 0 0 8px rgba(34, 197, 94, 0); }
  100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
}

@keyframes pulse-warning {
  0% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7); }
  70% { box-shadow: 0 0 0 10px rgba(245, 158, 11, 0); }
  100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
}

@keyframes pulse-error {
  0% { box-shadow: 0 0 0 0 rgba(244, 63, 94, 0.7); }
  70% { box-shadow: 0 0 0 10px rgba(244, 63, 94, 0); }
  100% { box-shadow: 0 0 0 0 rgba(244, 63, 94, 0); }
}

@keyframes pulse-alert {
  0% { box-shadow: 0 0 0 0 rgba(244, 63, 94, 0.9); }
  50% { box-shadow: 0 0 0 15px rgba(244, 63, 94, 0.3); }
  100% { box-shadow: 0 0 0 0 rgba(244, 63, 94, 0); }
}

@keyframes new-alert-in {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style> 
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
    const activeCameras = ref([0]) // 默认激活第一个摄像头
    
    const cameras = ref([
      { id: 0, name: '三楼机房1号点位', active: true },
      { id: 1, name: '三楼机房2号点位', active: false },
      { id: 2, name: '三楼机房3号点位', active: false },
      { id: 3, name: '四楼机房1号点位', active: false },
      { id: 4, name: '四楼机房2号点位', active: false },
      { id: 5, name: '四楼机房3号点位', active: false },
      { id: 6, name: '五楼机房1号点位', active: false },
      { id: 7, name: '五楼机房2号点位', active: false },
      { id: 8, name: '五楼机房3号点位', active: false }
    ])

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
      const locations = {
        0: '三楼机房1号点位', 1: '三楼机房2号点位', 2: '三楼机房3号点位',
        3: '四楼机房1号点位', 4: '四楼机房2号点位', 5: '四楼机房3号点位',
        6: '五楼机房1号点位', 7: '五楼机房2号点位', 8: '五楼机房3号点位'
      }

      const alert = {
        id: Date.now(),
        location: locations[data.camera_id] || '未知位置',
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
      const camera = cameras.value.find(c => c.id === cameraId)
      if (camera) {
        camera.active = !camera.active
        if (camera.active) {
          activeCameras.value.push(cameraId)
        } else {
          activeCameras.value = activeCameras.value.filter(id => id !== cameraId)
        }
      }
    }

    onMounted(() => {
      updateTime()
      timeInterval = setInterval(updateTime, 1000)
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
      toggleCamera
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
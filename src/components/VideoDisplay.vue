<template>
  <main class="content-area">
    <div class="camera-list">
      <div class="camera-list-header">
        <h2>摄像头列表</h2>
        <button 
          class="refresh-btn"
          @click="refreshDevices"
          :disabled="isRefreshing"
          :title="isRefreshing ? '正在刷新...' : '刷新设备列表'"
        >
          <span class="refresh-icon" :class="{ 'rotating': isRefreshing }">🔄</span>
        </button>
      </div>
      <div class="camera-groups">
        <div 
          v-for="(groupDevices, groupName) in groupedCameras" 
          :key="groupName"
          class="camera-group"
        >
          <div class="group-header">
            <span class="group-name">{{ groupName }}</span>
            <span class="group-count">({{ groupDevices.length }})</span>
          </div>
          <div 
            v-for="camera in groupDevices" 
            :key="camera.id"
            class="camera-item"
            :class="{ 'active': camera.active }"
            @click="toggleCamera(camera.id)"
          >
            <div class="camera-info">
              <div class="camera-name">{{ camera.name }}</div>
              <div class="camera-details">
                <span class="camera-ip">{{ camera.ip }}</span>
                <span class="camera-type">{{ getDeviceTypeName(camera.type) }}</span>
              </div>
            </div>
            <div class="camera-status" :class="camera.status">
              {{ camera.status === 'active' ? '在线' : '离线' }}
            </div>
          </div>
        </div>
      </div>
    </div>
    <div 
      class="video-display"
      :class="videoDisplayClass"
    >
      <div 
        v-for="camera in cameras" 
        :key="camera.id"
        class="video-card"
        :class="{ 'active': camera.active }"
        :data-camera-id="camera.id"
      >
        <div class="video-title">{{ camera.name }}</div>
        <div 
          v-if="!camera.active"
          class="video-placeholder"
        >
          未激活
        </div>
        <div 
          v-else-if="camera.status === 'inactive'"
          class="video-placeholder"
        >
          设备离线
        </div>
        <img 
          v-else
          :src="getVideoUrl(camera.id)"
          class="video-container"
          @load="onVideoLoad"
          @error="onVideoError"
        >
      </div>
    </div>
  </main>
</template>

<script>
import { computed, ref } from 'vue'
import { API_CONFIG } from '../config/api.js'

export default {
  name: 'VideoDisplay',
  props: {
    cameras: {
      type: Array,
      required: true
    },
    activeCameras: {
      type: Array,
      required: true
    }
  },
  emits: ['toggle-camera', 'refresh-devices'],
  setup(props, { emit }) {
    const isRefreshing = ref(false)
    
    // 按分组组织摄像头数据
    const groupedCameras = computed(() => {
      const groups = {}
      
      props.cameras.forEach(camera => {
        const groupName = camera.groupName || '未分配摄像头'
        if (!groups[groupName]) {
          groups[groupName] = []
        }
        groups[groupName].push(camera)
      })
      
      return groups
    })

    // 刷新设备列表
    const refreshDevices = async () => {
      if (isRefreshing.value) return
      
      isRefreshing.value = true
      try {
        emit('refresh-devices')
      } catch (error) {
        console.error('刷新设备列表失败:', error)
      } finally {
        // 延迟重置状态，给用户视觉反馈
        setTimeout(() => {
          isRefreshing.value = false
        }, 1000)
      }
    }

    const videoDisplayClass = computed(() => {
      const activeCount = props.activeCameras.length
      if (activeCount > 4) {
        return 'multi-view'
      } else if (activeCount === 1) {
        return 'single-view'
      }
      return ''
    })

    const toggleCamera = (cameraId) => {
      emit('toggle-camera', cameraId)
    }

    const getVideoUrl = (cameraId) => {
      return API_CONFIG.VIDEO_STREAM.getUrl(cameraId)
    }

    // 将设备类型数字转换为可读的名称
    const getDeviceTypeName = (type) => {
      const typeMap = {
        '1': '网络摄像头',
        '2': 'IP摄像头',
        '3': '监控摄像头',
        '4': '球机',
        '5': '枪机',
        '6': '半球',
        '7': '鱼眼',
        '8': '全景',
        '9': '热成像',
        '10': '门禁摄像头'
      }
      return typeMap[type] || `类型${type}`
    }

    const onVideoLoad = (event) => {
      const img = event.target
      const placeholder = img.parentElement.querySelector('.video-placeholder')
      img.style.display = 'block'
      if (placeholder) {
        placeholder.style.display = 'none'
      }
    }

    const onVideoError = (event) => {
      const img = event.target
      const placeholder = img.parentElement.querySelector('.video-placeholder')
      img.style.display = 'none'
      if (placeholder) {
        placeholder.style.display = 'block'
        placeholder.textContent = '视频流错误'
      }
    }

    return {
      groupedCameras,
      videoDisplayClass,
      toggleCamera,
      getVideoUrl,
      getDeviceTypeName,
      onVideoLoad,
      onVideoError,
      refreshDevices,
      isRefreshing
    }
  }
}
</script>

<style scoped>
.content-area {
  flex-grow: 1;
  padding: 24px;
  overflow-y: auto;
  background-color: transparent;
  display: flex;
  gap: 24px;
}

.camera-list {
  width: 320px;
  padding: 16px;
  flex-shrink: 0;
  background-color: var(--glass-bg);
  border: 1px solid var(--glass-border-color);
  border-radius: 12px;
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
}

.camera-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--glass-border-color);
}

.camera-list h2 {
  font-size: 16px;
  color: var(--font-color);
  margin: 0;
}

.refresh-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  transition: var(--base-transition);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--font-color-secondary);
}

.refresh-btn:hover:not(:disabled) {
  background-color: var(--glass-hover-bg);
  color: var(--primary-color);
  transform: scale(1.1);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.refresh-icon {
  font-size: 16px;
  transition: transform 0.3s ease;
}

.refresh-icon.rotating {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.camera-groups {
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.camera-group {
  margin-bottom: 20px;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 8px;
  background-color: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--primary-color);
}

.group-name {
  font-weight: 600;
}

.group-count {
  font-size: 12px;
  color: var(--font-color-secondary);
  font-weight: normal;
}

.camera-item {
  padding: 12px 16px;
  margin-bottom: 8px;
  background-color: transparent;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: var(--base-transition);
  position: relative;
  overflow: hidden;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.camera-info {
  flex: 1;
  min-width: 0;
}

.camera-name {
  font-weight: 500;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.camera-details {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--font-color-secondary);
}

.camera-ip, .camera-type {
  background-color: rgba(148, 163, 184, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}

.camera-item:hover {
  background-color: var(--glass-hover-bg);
  border-color: var(--primary-color);
  transform: translateY(-2px);
}

.camera-item.active {
  color: white;
  background-color: var(--primary-color);
  border-color: var(--primary-color);
  box-shadow: 0 0 20px var(--primary-glow-color);
}

.camera-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
}

.camera-status.active {
  background-color: var(--success-color);
  color: white;
}

.camera-status.inactive {
  background-color: var(--danger-color);
  color: white;
}

.video-display {
  flex-grow: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
  align-content: start;
}

.video-display.multi-view {
  grid-template-columns: repeat(3, 1fr);
}

.video-display.single-view {
  grid-template-columns: 1fr;
}

.video-display.single-view .video-card {
  max-width: 100%;
  max-height: calc(100vh - 120px);
}

.video-card {
  position: relative;
  background-color: #000;
  overflow: hidden;
  aspect-ratio: 16 / 10;
  display: none;
  border-radius: 12px;
  border: 1px solid var(--glass-border-color);
  box-shadow: 0 8px 25px rgba(0,0,0,0.4);
  transition: var(--base-transition);
  transform: scale(1);
}

.video-placeholder {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: var(--font-color);
  font-size: 1.5rem;
  font-weight: bold;
  text-shadow: 0 0 10px var(--primary-glow-color);
  opacity: 0.7;
  z-index: 1;
  display: block;
  text-align: center;
}

.video-card.active .video-placeholder {
  display: block;
}

.video-card:hover {
  transform: scale(1.03);
  z-index: 10;
}

.video-card.active {
  display: block;
  border: 1px solid var(--primary-color);
  box-shadow: 0 0 25px var(--primary-glow-color), 0 8px 25px rgba(0,0,0,0.4);
}

.video-title {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to bottom, rgba(0,0,0,0.8), transparent);
  color: white;
  padding: 12px;
  font-size: 0.9rem;
  font-weight: 500;
  z-index: 1;
  transition: var(--base-transition);
}

.video-container {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: none;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .video-display.multi-view {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .content-area {
    flex-direction: column;
    gap: 16px;
  }
  
  .camera-list {
    width: 100%;
  }
  
  .camera-groups {
    max-height: 300px;
  }
  
  .video-display {
    grid-template-columns: 1fr;
  }
  
  .video-display.multi-view {
    grid-template-columns: 1fr;
  }
}
</style> 
<template>
  <main class="content-area">
    <div class="camera-list">
      <h2>摄像头列表</h2>
      <div 
        v-for="camera in cameras" 
        :key="camera.id"
        class="camera-item"
        :class="{ 'active': camera.active }"
        @click="toggleCamera(camera.id)"
      >
        {{ camera.name }}
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
          v-if="camera.id === 0 && camera.active"
          class="video-placeholder"
          style="display: none;"
        >
          陕西国网
        </div>
        <div 
          v-else
          class="video-placeholder"
        >
          {{ camera.id === 0 ? '陕西国网' : '暂无视频流' }}
        </div>
        <img 
          v-if="camera.id === 0 && camera.active"
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
import { computed } from 'vue'
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
  emits: ['toggle-camera'],
  setup(props, { emit }) {
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
      }
    }

    return {
      videoDisplayClass,
      toggleCamera,
      getVideoUrl,
      onVideoLoad,
      onVideoError
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
  width: 280px;
  padding: 16px;
  flex-shrink: 0;
  background-color: var(--glass-bg);
  border: 1px solid var(--glass-border-color);
  border-radius: 12px;
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
}

.camera-list h2 {
  font-size: 16px;
  margin-bottom: 16px;
  color: var(--font-color);
  padding-bottom: 12px;
  border-bottom: 1px solid var(--glass-border-color);
  text-align: center;
}

.camera-item {
  padding: 12px 16px;
  margin-bottom: 10px;
  background-color: transparent;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: var(--base-transition);
  position: relative;
  overflow: hidden;
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
  font-size: 2rem;
  font-weight: bold;
  text-shadow: 0 0 10px var(--primary-glow-color);
  opacity: 0.7;
  z-index: 1;
  display: block;
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
  border-radius: 12px;
  display: none;
}
</style> 
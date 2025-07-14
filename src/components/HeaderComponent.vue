<template>
  <header class="main-header">
    <div class="header-left">
      <img src="/static/logo.jpg" alt="Logo">
      <h1>陕西国网无计划作业检测系统</h1>
    </div>
    <div class="header-right">
      <div class="status-display">
        <span 
          class="status-indicator"
          :class="statusClass"
          :style="statusStyle"
        ></span>
        <span>{{ connectionStatus.message }}</span>
      </div>
      <div class="current-time">{{ currentTime }}</div>
      <i class="fa-solid fa-expand" title="全屏" @click="toggleFullscreen"></i>
      <i class="fa-solid fa-gear" title="设置" @click="openSettings"></i>
      <i class="fa-solid fa-circle-user" title="用户" @click="openUserPanel"></i>
    </div>
  </header>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'HeaderComponent',
  props: {
    currentTime: {
      type: String,
      required: true
    },
    connectionStatus: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const statusClass = computed(() => {
      return `status-${props.connectionStatus.status}`
    })

    const statusStyle = computed(() => {
      const styles = {
        connected: {
          backgroundColor: 'var(--success-color)',
          animation: 'pulse-success 2s infinite'
        },
        disconnected: {
          backgroundColor: '#f59e0b',
          animation: 'pulse-warning 1s infinite'
        },
        error: {
          backgroundColor: 'var(--danger-color)',
          animation: 'pulse-error 1s infinite'
        },
        alert: {
          backgroundColor: 'var(--danger-color)',
          animation: 'pulse-alert 0.5s infinite'
        }
      }
      return styles[props.connectionStatus.status] || styles.connected
    })

    const toggleFullscreen = () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen()
      } else {
        document.exitFullscreen()
      }
    }

    const openSettings = () => {
      console.log('打开设置')
      // TODO: 实现设置功能
    }

    const openUserPanel = () => {
      console.log('打开用户面板')
      // TODO: 实现用户面板功能
    }

    return {
      statusClass,
      statusStyle,
      toggleFullscreen,
      openSettings,
      openUserPanel
    }
  }
}
</script>

<style scoped>
.main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 24px;
  flex-shrink: 0;
  background-color: var(--glass-bg);
  border-bottom: 1px solid var(--glass-border-color);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left img {
  height: 32px;
  width: auto;
  border-radius: 50%;
}

.header-left h1 {
  font-size: 20px;
  font-weight: 600;
  text-shadow: 0 0 8px rgba(226, 232, 240, 0.3);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
  color: var(--font-color-secondary);
}

.header-right i {
  font-size: 1.1rem;
  cursor: pointer;
  transition: var(--base-transition);
}

.header-right i:hover {
  color: var(--font-color);
  transform: scale(1.1);
  text-shadow: 0 0 10px var(--primary-glow-color);
}

.status-display {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: var(--success-color);
  animation: pulse-success 2s infinite;
}

.current-time {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.9rem;
}
</style> 
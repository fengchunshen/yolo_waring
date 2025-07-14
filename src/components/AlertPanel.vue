<template>
  <aside class="side-panel">
    <div class="panel-header">
      <i class="fa-solid fa-triangle-exclamation"></i>
      实时告警信息
    </div>
    <div class="panel-content">
      <div 
        v-for="alert in alerts" 
        :key="alert.id"
        class="alert-item"
        :class="{ 'new-alert': alert.isNew }"
      >
        <h3>
          <i class="fa-solid fa-shield-virus"></i>
          检测到无计划作业
        </h3>
        <p><strong>位置:</strong> {{ alert.location }}</p>
        <p><strong>置信度:</strong> {{ alert.confidence }}%</p>
        <p><strong>人员ID:</strong> {{ alert.personId }}</p>
        <p><strong>持续时间:</strong> {{ alert.duration }}秒</p>
        <p class="alert-time">{{ alert.timestamp }}</p>
      </div>
      <div v-if="alerts.length === 0" class="no-alerts">
        <i class="fa-solid fa-check-circle"></i>
        <p>暂无告警信息</p>
      </div>
    </div>
  </aside>
</template>

<script>
export default {
  name: 'AlertPanel',
  props: {
    alerts: {
      type: Array,
      required: true
    }
  }
}
</script>

<style scoped>
.side-panel {
  width: 320px;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  background-color: var(--glass-bg);
  border-right: 1px solid var(--glass-border-color);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  transition: var(--base-transition);
}

.panel-header {
  padding: 16px;
  font-size: 16px;
  font-weight: 600;
  text-align: center;
  border-bottom: 1px solid var(--glass-border-color);
  flex-shrink: 0;
  color: var(--danger-color);
  text-shadow: 0 0 8px var(--danger-glow-color);
}

.panel-content {
  flex-grow: 1;
  overflow-y: auto;
  padding: 16px 8px;
}

.panel-content::-webkit-scrollbar {
  width: 6px;
}

.panel-content::-webkit-scrollbar-track {
  background: transparent;
}

.panel-content::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

.panel-content::-webkit-scrollbar-thumb:hover {
  background: var(--primary-color);
}

.alert-item {
  background-color: rgba(244, 63, 94, 0.1);
  border: 1px solid rgba(244, 63, 94, 0.3);
  border-radius: 8px;
  padding: 12px 16px;
  margin: 0 8px 12px;
  transition: var(--base-transition);
  transform: scale(1);
}

.alert-item.new-alert {
  animation: new-alert-in 0.5s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.alert-item:hover {
  background-color: rgba(244, 63, 94, 0.2);
  border-color: var(--danger-color);
  transform: scale(1.02);
  box-shadow: 0 0 15px var(--danger-glow-color);
}

.alert-item h3 {
  color: var(--danger-color);
  margin-bottom: 8px;
  font-size: 1rem;
  display: flex;
  align-items: center;
  gap: 8px;
}

.alert-item p {
  margin: 4px 0;
  font-size: 0.9rem;
  color: var(--font-color-secondary);
}

.alert-item p strong {
  color: var(--font-color);
  font-weight: 500;
}

.alert-time {
  font-size: 0.8rem;
  color: #64748b;
  margin-top: 8px;
  text-align: right;
}

.no-alerts {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px 20px;
  color: var(--font-color-secondary);
}

.no-alerts i {
  font-size: 2rem;
  color: var(--success-color);
}

.no-alerts p {
  font-size: 0.9rem;
}
</style> 
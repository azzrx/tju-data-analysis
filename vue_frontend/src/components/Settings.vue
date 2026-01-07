<template>
  <div class="settings-overlay" @click="closeSettings">
    <div class="settings-modal" @click.stop>
      <div class="settings-header">
        <h2>设置</h2>
        <button class="close-btn" @click="closeSettings">✕</button>
      </div>
      
      <div class="settings-content">
        <div class="settings-section">
          <h3>模型选择</h3>
          <div class="setting-item">
            <label>当前模型</label>
            <div class="model-select">
              <select v-model="selectedModel">
                <option v-for="opt in models" :key="opt.key" :value="opt.key">
                  {{ opt.name }} — {{ opt.llm }}
                </option>
              </select>
              <button class="switch-btn" @click="switchModel">切换</button>
            </div>
            <p class="help-text">切换模型会在后端重新初始化模型实例（可能需要一些时间）。如果切换到本地模型，请确认已在服务器上执行 <code>ollama pull gemma3:latest</code>。</p>
          </div>
        </div>
        <div class="settings-section">
          <h3>常规 - 外观</h3>
          
          <div class="setting-item">
            <label>主题模式</label>
            <div class="theme-options">
              <button
                :class="['theme-btn', { active: currentTheme === 'light' }]"
                @click="setTheme('light')"
              >
                ☀️ 浅色
              </button>
              <button
                :class="['theme-btn', { active: currentTheme === 'dark' }]"
                @click="setTheme('dark')"
              >
                🌙 深色
              </button>
              <button
                :class="['theme-btn', { active: currentTheme === 'auto' }]"
                @click="setTheme('auto')"
              >
                💻 跟随系统
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, defineEmits } from 'vue';
import { useStore } from '../store';
import api from '../api';

const emits = defineEmits(['close']);

const currentTheme = ref('auto');
const store = useStore();

const models = ref([]);
const selectedModel = ref('');

onMounted(() => {
  // 从 store 获取模型列表（Chat.vue 已经触发加载），否则从 API 拉取
  if (store.models && store.models.length > 0) {
    models.value = store.models;
    selectedModel.value = store.currentModel || (models.value[0] && models.value[0].key);
  } else {
    api.getModels().then(resp => {
      const data = resp?.data || {};
      models.value = data.options || [];
      selectedModel.value = data.current || (models.value[0] && models.value[0].key);
      store.setModelOptions(models.value);
      store.setCurrentModel(selectedModel.value);
    }).catch(() => {});
  }
});

const switchModel = async () => {
  if (!selectedModel.value) return;
  try {
    const resp = await api.switchModel(selectedModel.value);
    const data = resp?.data || {};
    if (data.options) store.setModelOptions(data.options);
    if (data.current) store.setCurrentModel(data.current);
    alert('模型切换成功: ' + data.current);
  } catch (err) {
    alert('模型切换失败: ' + (err.response?.data?.error || err.message));
  }
};

// 获取当前主题
onMounted(() => {
  const savedTheme = localStorage.getItem('theme') || 'auto';
  currentTheme.value = savedTheme;
});

// 设置主题
const setTheme = (theme) => {
  currentTheme.value = theme;
  localStorage.setItem('theme', theme);
  applyTheme(theme);
};

// 应用主题
const applyTheme = (theme) => {
  const root = document.documentElement;
  
  if (theme === 'auto') {
    // 跟随系统
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    root.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
  } else {
    root.setAttribute('data-theme', theme);
  }
};

const closeSettings = () => {
  emits('close');
};
</script>

<style scoped>
.settings-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.settings-modal {
  background-color: var(--bg-color);
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.settings-header h2 {
  margin: 0;
  font-size: 1.25rem;
  color: var(--text-color);
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.close-btn:hover {
  background-color: var(--hover-color);
}

.settings-content {
  padding: 1.5rem;
  overflow-y: auto;
  max-height: calc(80vh - 80px);
}

.settings-section {
  margin-bottom: 2rem;
}

.settings-section h3 {
  font-size: 1rem;
  margin-bottom: 1rem;
  color: var(--text-color);
}

.setting-item {
  margin-bottom: 1.5rem;
}

.setting-item label {
  display: block;
  margin-bottom: 0.75rem;
  font-weight: 500;
  color: var(--text-color);
}

.theme-options {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.theme-btn {
  flex: 1;
  min-width: 100px;
  padding: 0.75rem 1rem;
  border: 2px solid var(--border-color);
  background-color: var(--bg-secondary);
  color: var(--text-color);
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.theme-btn:hover {
  border-color: var(--primary-color);
  background-color: var(--hover-color);
}

.theme-btn.active {
  border-color: var(--primary-color);
  background-color: var(--primary-color);
  color: white;
}
</style>


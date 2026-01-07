<template>
  <div class="session-list">
    <div class="session-list-header">
      <h2>会话</h2>
      <button class="primary" @click="showNewSessionDialog = true">
        <plus-icon class="icon" />
      </button>
    </div>
    
    <div class="session-items">
      <div
        v-for="session in sessions"
        :key="session"
        class="session-item"
        :class="{ active: session === currentSession }"
        @click="selectSession(session)"
        @contextmenu.prevent="showContextMenu($event, session)"
      >
        <div class="session-content">
          <div class="session-name">{{ session }}</div>
          <div class="session-meta" v-if="getLastMessage(session)">
            <span class="session-preview">{{ getLastMessage(session).preview }}</span>
            <span class="session-time">{{ getLastMessage(session).time }}</span>
          </div>
        </div>
        <button 
          class="delete-btn" 
          @click.stop="deleteSession(session)"
          title="删除会话"
        >
          <trash-icon class="icon" />
        </button>
      </div>
    </div>
    
    <!-- 右键菜单 -->
    <div v-if="contextMenu.show" 
         class="context-menu" 
         :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
         @click.stop>
      <button class="context-menu-item" @click="renameSession(contextMenu.session)">
        <span>重命名</span>
      </button>
      <button class="context-menu-item" @click="deleteSession(contextMenu.session)">
        <span>删除</span>
      </button>
    </div>
    
    <!-- 新建会话对话框 -->
    <div v-if="showNewSessionDialog" class="dialog-overlay">
      <div class="dialog">
        <h3>新建会话</h3>
        <input
          type="text"
          v-model="newSessionName"
          placeholder="输入会话名称"
          @keyup.enter="createSession"
        />
        <div class="dialog-buttons">
          <button class="secondary" @click="showNewSessionDialog = false">取消</button>
          <button class="primary" @click="createSession">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits } from 'vue';
import { PlusIcon, TrashIcon } from 'vue-tabler-icons';

const props = defineProps({
  sessions: {
    type: Array,
    required: true
  },
  currentSession: {
    type: String,
    required: true
  },
  messages: {
    type: Object,
    default: () => ({})
  }
});

const emits = defineEmits(['select', 'delete', 'create', 'rename']);

const showNewSessionDialog = ref(false);
const newSessionName = ref('');
const contextMenu = ref({ show: false, x: 0, y: 0, session: '' });

const selectSession = (session) => {
  emits('select', session);
  contextMenu.value.show = false;
};

const deleteSession = (session) => {
  contextMenu.value.show = false;
  if (confirm(`确定要删除会话 "${session}" 吗？`)) {
    emits('delete', session);
  }
};

const renameSession = (session) => {
  contextMenu.value.show = false;
  const newName = prompt(`重命名会话 "${session}"`, session);
  if (newName && newName.trim() && newName !== session) {
    emits('rename', session, newName.trim());
  }
};

const createSession = () => {
  if (newSessionName.value.trim()) {
    emits('create', newSessionName.value.trim());
    newSessionName.value = '';
    showNewSessionDialog.value = false;
  }
};

const getLastMessage = (sessionId) => {
  const sessionMessages = props.messages[sessionId];
  if (!sessionMessages || sessionMessages.length === 0) {
    return null;
  }
  const lastMsg = sessionMessages[sessionMessages.length - 1];
  const preview = lastMsg.content.length > 30 
    ? lastMsg.content.substring(0, 30) + '...' 
    : lastMsg.content;
  const time = new Date(lastMsg.timestamp).toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: false 
  });
  return { preview, time };
};

const showContextMenu = (event, session) => {
  contextMenu.value = {
    show: true,
    x: event.clientX,
    y: event.clientY,
    session
  };
  // 点击其他地方关闭菜单
  const closeMenu = () => {
    contextMenu.value.show = false;
    document.removeEventListener('click', closeMenu);
  };
  setTimeout(() => {
    document.addEventListener('click', closeMenu);
  }, 0);
};
</script>

<style scoped>
.session-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  border-right: 1px solid var(--border-color);
  animation: fadeInSlide 0.3s ease-out;
}

@keyframes fadeInSlide {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.session-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--border-color);
}

.session-list-header h2 {
  font-size: 1.25rem;
  font-weight: 600;
}

.icon {
  width: 1.25rem;
  height: 1.25rem;
}

.session-items {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  border-radius: var(--radius);
  margin-bottom: 0.5rem;
  cursor: pointer;
  transition: background-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
  animation: slideInItem 0.3s ease-out backwards;
  position: relative;
}

.session-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.session-name {
  font-weight: 500;
  font-size: 0.9375rem;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
}

.session-preview {
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.session-time {
  color: var(--text-tertiary, #64748b);
  white-space: nowrap;
  flex-shrink: 0;
}

@keyframes slideInItem {
  from {
    opacity: 0;
    transform: translateX(-15px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 为每个会话项添加延迟动画 */
.session-item:nth-child(1) { animation-delay: 0.05s; }
.session-item:nth-child(2) { animation-delay: 0.1s; }
.session-item:nth-child(3) { animation-delay: 0.15s; }
.session-item:nth-child(4) { animation-delay: 0.2s; }
.session-item:nth-child(5) { animation-delay: 0.25s; }
.session-item:nth-child(n+6) { animation-delay: 0.3s; }

.session-item:hover {
  background-color: var(--hover-color, var(--bg-secondary));
}

.session-item.active {
  background-color: var(--primary-color);
  color: white;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.session-item.active .session-name,
.session-item.active .session-preview,
.session-item.active .session-time {
  color: white;
}

.delete-btn {
  background: none;
  padding: 0.25rem;
  opacity: 0.7;
  display: none;
}

.session-item:hover .delete-btn {
  display: block;
}

.session-item.active .delete-btn {
  color: white;
}

.delete-btn:hover {
  opacity: 1;
  background-color: rgba(0, 0, 0, 0.1);
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 100;
}

.dialog {
  background-color: var(--card-bg);
  border-radius: var(--radius);
  padding: 1.5rem;
  width: 100%;
  max-width: 400px;
}

.dialog h3 {
  margin-bottom: 1rem;
  font-size: 1.25rem;
}

.dialog input {
  width: 100%;
  margin-bottom: 1rem;
}

.dialog-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.context-menu {
  position: fixed;
  background-color: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  z-index: 1000;
  min-width: 120px;
  padding: 0.25rem;
}

.context-menu-item {
  width: 100%;
  padding: 0.5rem 0.75rem;
  text-align: left;
  background: none;
  border: none;
  color: var(--text-primary);
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.2s ease;
  font-size: 0.875rem;
}

.context-menu-item:hover {
  background-color: var(--hover-color, var(--bg-secondary));
}
</style>

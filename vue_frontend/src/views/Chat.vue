<template>
  <div class="chat-container">
    <div class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <SessionList
        :sessions="sessions"
        :current-session="currentSession"
        :messages="store.messages"
        @select="handleSelectSession"
        @delete="handleDeleteSession"
        @create="handleCreateSession"
        @rename="handleRenameSession"
      />

      <div class="user-info">
        <div class="user-actions">
          <button class="icon-btn" @click="handleClearHistory" title="清空当前会话">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
          <button class="icon-btn logout-btn" @click="handleLogout" title="退出登录">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <div class="chat-area">
      <div class="chat-header">
        <button 
          class="sidebar-toggle-btn" 
          @click="toggleSidebar"
          :title="sidebarCollapsed ? '展开会话栏' : '收起会话栏'"
        >
          <svg v-if="sidebarCollapsed" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <polyline points="9 6 15 12 9 18"></polyline>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="21" y1="12" x2="3" y2="12"></line>
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>
        
        <div class="header-center">
          <div class="anime-character" @click="characterClick">
            <div class="character-container">
              <img 
                src="https://api.dicebear.com/7.x/lorelei/svg?seed=LogOracle&backgroundColor=b6e3ff,c0aede,d1d4f9,ffd5dc,ffdfbf&radius=50&hair=variant01,variant02,variant03,variant04&hairColor=0e0e0e,3c4a5b,6c757d&clothing=variant01,variant02,variant03" 
                alt="可爱女角色"
                class="character-img"
                @error="handleImageError"
              />
              <div class="sparkle sparkle-1">✨</div>
              <div class="sparkle sparkle-2">⭐</div>
              <div class="sparkle sparkle-3">💫</div>
            </div>
            <div class="character-bubble" v-if="showBubble">
              <span>{{ bubbleText }}</span>
            </div>
          </div>
          <h1 class="header-title">
            <span class="title-main">LogOracle</span>
            <span class="subtitle-cn">日志神谕</span>
          </h1>
          <p class="header-desc">智能日志分析平台 · 洞察系统真相</p>
          <h2 class="header-session">当前会话: {{ currentSession }}</h2>
        </div>
        
        <div class="header-actions">
          <button class="plus-btn" @click="showPricingModal = true" title="获取 Plus">
            <span class="plus-icon">✨</span>
            <span class="plus-text">Plus</span>
          </button>
          <button class="settings-btn" @click="showSettings = true" title="设置">
            ⚙️
          </button>
        </div>
      </div>

      <!-- 定价卡片模态框 -->
      <div v-if="showPricingModal" class="pricing-modal-overlay" @click="showPricingModal = false">
        <div class="pricing-card" @click.stop>
          <button class="close-btn" @click="showPricingModal = false" title="关闭">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
          <div class="pricing-badge">
            <span class="badge-text">MOST POPULAR</span>
            <span class="badge-icon">⭐</span>
          </div>
          <div class="pricing-content">
            <h3 class="plan-name">Profesional</h3>
            <div class="price-section">
              <span class="price">$98,00</span>
              <span class="price-period">/ month</span>
            </div>
            <p class="plan-description">Best for growing startups and growth companies</p>
            <button class="signup-btn" @click="handleSignUp">
              Become a Pro
            </button>
          </div>
        </div>
      </div>

      <div v-if="error" class="error-message">{{ error }}</div>

      <div class="messages-container" ref="messagesContainer">
        <div v-if="messages.length === 0" class="empty-state">
          <div class="welcome-content">
            <h3>欢迎使用 LogOracle 日志神谕</h3>
            <p class="subtitle">基于 RAG 技术的智能日志分析平台</p>
            
            <div class="features">
              <div class="feature-card">
                <div class="feature-icon">🔍</div>
                <div class="feature-text">
                  <div class="feature-title">智能检索</div>
                  <div class="feature-desc">快速定位相关日志</div>
                </div>
              </div>
              <div class="feature-card">
                <div class="feature-icon">💡</div>
                <div class="feature-text">
                  <div class="feature-title">深度分析</div>
                  <div class="feature-desc">AI 驱动的专业分析</div>
                </div>
              </div>
              <div class="feature-card">
                <div class="feature-icon">🎯</div>
                <div class="feature-text">
                  <div class="feature-title">精准诊断</div>
                  <div class="feature-desc">识别问题根因</div>
                </div>
              </div>
              <div class="feature-card">
                <div class="feature-icon">📊</div>
                <div class="feature-text">
                  <div class="feature-title">多维度洞察</div>
                  <div class="feature-desc">全面的系统分析</div>
                </div>
              </div>
            </div>

            <div class="example-queries">
              <p class="example-title">💬 试试这些问题：</p>
              <div class="query-examples">
                <button 
                  class="example-query" 
                  @click="handleExampleQuery('分析最近的错误日志')"
                >
                  "分析最近的错误日志"
                </button>
                <button 
                  class="example-query" 
                  @click="handleExampleQuery('系统性能瓶颈在哪里？')"
                >
                  "系统性能瓶颈在哪里？"
                </button>
                <button 
                  class="example-query" 
                  @click="handleExampleQuery('有哪些安全警告？')"
                >
                  "有哪些安全警告？"
                </button>
              </div>
            </div>

            <p class="start-hint">开始提问，让 LogOracle 为您揭示日志中的真相</p>
          </div>
        </div>

        <ChatMessage
          v-for="msg in messages"
          :key="msg.id"
          :is-user="msg.isUser"
          :content="msg.content"
          :timestamp="msg.timestamp"
        />

        <div v-if="loading" class="loading-indicator">
          <div class="loading"></div>
          <p>LogOracle 正在分析日志，洞察真相中...</p>
        </div>
      </div>

      <ChatInput :loading="loading" @send="handleSendMessage" @stop="handleStopGeneration" />
    </div>

    <!-- 设置弹窗 -->
    <Settings v-if="showSettings" @close="showSettings = false" />
  </div>
</template>

<script setup>
import { onMounted, computed, ref, watch, nextTick } from "vue";
import { useRouter } from "vue-router";
import { useStore } from "../store";
import api from "../api";
import SessionList from "../components/SessionList.vue";
import ChatMessage from "../components/ChatMessage.vue";
import ChatInput from "../components/ChatInput.vue";
import Settings from "../components/Settings.vue";

const store = useStore();
const router = useRouter();

// 用于取消流式请求的 AbortController
let abortController = null;

// 设置弹窗显示状态
const showSettings = ref(false);

// 侧边栏收起状态（默认收起）
const sidebarCollapsed = ref(true);
const showPricingModal = ref(false);
const showBubble = ref(false);
const bubbleText = ref('');
// 消息滚动容器，用于在新内容抵达时自动滚动到底部
const messagesContainer = ref(null);

// 二次元小人点击事件
const characterClick = () => {
  const texts = [
    '你好呀！✨',
    '需要帮助吗？😊',
    '一起分析日志吧！💪',
    'LogOracle 最棒了！🌟',
    '加油加油！🎉'
  ];
  bubbleText.value = texts[Math.floor(Math.random() * texts.length)];
  showBubble.value = true;
  setTimeout(() => {
    showBubble.value = false;
  }, 2000);
};

// 图片加载失败处理
const handleImageError = (event) => {
  // 如果图片加载失败，使用备用方案（可爱的女角色）
  event.target.src = 'https://api.dicebear.com/7.x/fun-emoji/svg?seed=LogOracle&backgroundColor=b6e3ff,c0aede,d1d4f9,ffd5dc';
  console.log('图片加载失败，使用备用图片');
};

// 切换侧边栏
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value;
  localStorage.setItem('sidebarCollapsed', sidebarCollapsed.value.toString());
};

// 从 localStorage 恢复侧边栏状态
onMounted(() => {
  const saved = localStorage.getItem('sidebarCollapsed');
  if (saved !== null) {
    sidebarCollapsed.value = saved === 'true';
  }
  // 首次加载历史后，等待渲染完成再滚动到底部
  loadHistory(currentSession.value).then(() => {
    nextTick(() => scrollToBottom());
  });
  loadModels();
});

// 计算属性
const sessions = computed(() => store.sessions);
const currentSession = computed(() => store.currentSession);
const messages = computed(() => store.messages[currentSession.value] || []);
const loading = computed(() => store.loading);
const error = computed(() => store.error);

// 将视图滚动到消息底部；当 smooth 为 true 时使用平滑动画，提升阅读体验
const scrollToBottom = (smooth = false) => {
  const container = messagesContainer.value;
  if (!container) return;
  container.scrollTo({
    top: container.scrollHeight,
    behavior: smooth ? 'smooth' : 'auto',
  });
};

// 监听消息内容的任何变更（包括流式增量），完成渲染后自动滚动到底部
watch(messages, () => {
  nextTick(() => scrollToBottom(true));
}, { deep: true });

// 当用户切换会话时，快速跳转到该会话消息列表的底部
watch(() => store.currentSession, () => {
  nextTick(() => scrollToBottom());
});

// 初始化加载历史记录
const loadHistory = async (sessionId) => {
  try {
    store.setLoading(true);
    const response = await api.getHistory(sessionId);
    // 确保响应数据存在
    const history = response?.data?.history || '';
    store.loadHistory(sessionId, history);
    // 历史数据写入后等待 DOM 更新，再滚动到最新位置
    await nextTick();
    scrollToBottom();
  } catch (err) {
    // 如果是 404 或空历史记录，这是正常的（新会话）
    if (err.response?.status === 404 || err.response?.status === 400) {
      // 新会话没有历史记录，确保消息数组为空
      if (!store.messages[sessionId]) {
        store.messages[sessionId] = [];
      }
    } else {
      store.setError(err.response?.data?.error || "加载历史记录失败");
    }
  } finally {
    store.setLoading(false);
  }
};

// 加载可用模型列表
const loadModels = async () => {
  try {
    const response = await api.getModels();
    const data = response?.data || {};
    if (data.options) {
      store.setModelOptions(data.options);
    }
    if (data.current) {
      store.setCurrentModel(data.current);
    } else if (!store.currentModel && data.options && data.options.length > 0) {
      store.setCurrentModel(data.options[0].key);
    }
  } catch (err) {
    console.error('加载模型配置失败:', err);
    store.setError(err.response?.data?.error || "加载模型配置失败");
  }
};


// 处理选择会话
const handleSelectSession = async (sessionId) => {
  // 先设置当前会话，确保界面立即更新
  store.setCurrentSession(sessionId);
  // 如果该会话没有消息，先初始化为空数组
  if (!store.messages[sessionId]) {
    store.messages[sessionId] = [];
  }
  // 然后加载历史记录
  try {
    await loadHistory(sessionId);
    // 切换会话后立即对齐底部，避免视图停留在旧位置
    await nextTick();
    scrollToBottom();
  } catch (err) {
    // 如果加载失败，确保消息数组存在
    if (!store.messages[sessionId]) {
      store.messages[sessionId] = [];
    }
    console.error('加载历史记录失败:', err);
  }
};

// 处理删除会话
const handleDeleteSession = async (sessionId) => {
  try {
    await api.clearHistory(sessionId);
    store.removeSession(sessionId);
    store.clearSessionMessages(sessionId);
  } catch (err) {
    store.setError(err.response?.data?.error || "删除会话失败");
  }
};

// 处理重命名会话
const handleRenameSession = (oldSessionId, newSessionId) => {
  // 更新会话列表
  const index = store.sessions.indexOf(oldSessionId);
  if (index !== -1) {
    store.sessions[index] = newSessionId;
    localStorage.setItem('sessions', JSON.stringify(store.sessions));
    
    // 如果重命名的是当前会话，更新当前会话
    if (oldSessionId === store.currentSession) {
      store.setCurrentSession(newSessionId);
    }
    
    // 迁移消息数据
    if (store.messages[oldSessionId]) {
      store.messages[newSessionId] = store.messages[oldSessionId];
      delete store.messages[oldSessionId];
    }
  }
};

// 处理创建会话
const handleCreateSession = async (sessionId) => {
  store.addSession(sessionId);
  // 确保新会话的消息数组被初始化
  if (!store.messages[sessionId]) {
    store.messages[sessionId] = [];
  } else {
    store.clearSessionMessages(sessionId);
  }
  // 尝试加载历史记录（新会话可能没有历史）
  try {
    await loadHistory(sessionId);
    // 新会话首次加载后也需要对齐底部，保持体验一致
    await nextTick();
    scrollToBottom();
  } catch (err) {
    // 新会话没有历史记录是正常的，忽略错误
    console.log('新会话，无历史记录');
  }
};

// 处理示例查询
const handleExampleQuery = (query) => {
  // 触发发送消息，使用默认的日志分析类型
  handleSendMessage(query, 'analysis');
};

const appendAttachmentReferences = (content) => {
  const sessionId = currentSession.value;
  if (!sessionId) {
    return content;
  }

  const files = store.getSessionFiles(sessionId) || [];
  if (!files.length) {
    return content;
  }

  const references = Array.from(
    new Set(
      files
        .map((file) => file?.path?.trim())
        .filter((path) => path && !content.includes(path))
    )
  );

  if (!references.length) {
    return content;
  }

  const attachmentBlock = references
    .map((path, index) => `[附件${index + 1}] ${path}`)
    .join('\n');

  return `${content}\n\n${attachmentBlock}`;
};

// 处理发送消息
const handleSendMessage = async (content, queryType) => {
  try {
    store.setLoading(true);
    
    // 创建新的 AbortController
    abortController = new AbortController();
    
    // 1. 先添加用户消息到界面
    const userMessageId = Date.now();
    store.addMessage(currentSession.value, true, content, userMessageId);
    
    // 2. 等待一小段时间，确保用户消息 ID 和 AI 消息 ID 不同
    await new Promise(resolve => setTimeout(resolve, 10));
    
    // 3. 添加一个空的 AI 回复消息占位，用于流式更新
    const botMessageId = Date.now();
    store.addMessage(currentSession.value, false, "", botMessageId);
    // 占位消息创建后滚动一次，避免回复在屏幕之外生成
    await nextTick();
    scrollToBottom(true);
 
    // 4. 使用流式 API，逐步更新 AI 回复
    const payloadContent = appendAttachmentReferences(content);

    await api.chatStream(
      currentSession.value,
      payloadContent,
      queryType,
      abortController.signal,  // 传递取消信号
      // onMessage: 收到增量内容时更新 AI 消息
      (fullContent) => {
        store.updateMessage(currentSession.value, botMessageId, fullContent);
        // 每次收到增量内容后请求一次平滑滚动，让用户实时看到生成过程
        nextTick(() => scrollToBottom(true));
      },
      // onError: 错误处理
      (error) => {
        if (error !== 'AbortError') {  // 忽略取消错误
          store.setError(error);
        }
        store.setLoading(false);
        abortController = null;
      },
      // onComplete: 完成
      (finalContent) => {
        store.updateMessage(currentSession.value, botMessageId, finalContent);
        store.setLoading(false);
        abortController = null;
        // 最后一段内容渲染完后再滚动一次，确保对齐底部
        nextTick(() => scrollToBottom(true));
      }
    );
  } catch (err) {
    if (err.name !== 'AbortError') {  // 忽略取消错误
      store.setError(err.message || "发送消息失败");
    }
    store.setLoading(false);
    abortController = null;
  }
};

// 处理停止生成
const handleStopGeneration = () => {
  if (abortController) {
    abortController.abort();
    
    // 找到最后一条 AI 消息，添加停止提示
    const sessionMessages = store.messages[currentSession.value];
    if (sessionMessages && sessionMessages.length > 0) {
      const lastMessage = sessionMessages[sessionMessages.length - 1];
      if (!lastMessage.isUser) {
        // 在 AI 回复后添加停止提示
        const currentContent = lastMessage.content || '';
        const updatedContent = currentContent + '\n\n---\n_用户停止生成_';
        store.updateMessage(currentSession.value, lastMessage.id, updatedContent);
      }
    }
    
    store.setLoading(false);
    abortController = null;
  }
};

// 处理清空历史
const handleClearHistory = async () => {
  if (confirm(`确定要清空当前会话 "${currentSession.value}" 的历史记录吗？`)) {
    try {
      await api.clearHistory(currentSession.value);
      store.clearSessionMessages(currentSession.value);
    } catch (err) {
      store.setError(err.response?.data?.error || "清空历史记录失败");
    }
  }
};

// 处理退出登录
const handleLogout = () => {
  if (confirm("确定要退出登录吗？")) {
    store.clearApiKey();
    router.push("/login");
  }
};

// 处理注册 Plus
const handleSignUp = () => {
  // TODO: 实现注册逻辑
  alert('正在跳转到注册页面...');
  showPricingModal.value = false;
};
</script>

<style scoped>
.chat-container {
  display: flex;
  height: 100vh;
  overflow: hidden; /* 防止整体页面被撑宽 */
  max-width: 100vw; /* 限制最大宽度为视口宽度 */
}

.sidebar {
  width: 300px;
  min-width: 300px;
  max-width: 300px;
  display: flex;
  flex-direction: column;
  background-color: var(--sidebar-bg, var(--bg-color));
  border-right: 1px solid var(--border-subtle, var(--border-color));
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), 
              opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              min-width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              max-width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  position: relative;
  z-index: 1;
  will-change: transform, opacity, width;
  opacity: 1;
}

.sidebar.collapsed {
  transform: translate3d(-100%, 0, 0);
  width: 0;
  min-width: 0;
  max-width: 0;
  opacity: 0;
  border-right: none;
  pointer-events: none;
}

/* 侧边栏内容动画 */
.sidebar > * {
  transition: opacity 0.2s ease, transform 0.2s ease;
  opacity: 1;
  transform: translateX(0);
}

.sidebar.collapsed > * {
  opacity: 0;
  transform: translateX(-10px);
  pointer-events: none;
}

.user-info {
  padding: 1rem;
  border-top: 1px solid var(--border-color);
  animation: fadeInUp 0.3s ease-out 0.2s backwards;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.user-actions {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
}

.icon-btn {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 0.5rem;
  border-radius: var(--radius);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
}

.icon-btn:hover {
  background: var(--hover-color);
  color: var(--text-primary);
  border-color: var(--border-color);
}

.logout-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger-color);
  border-color: rgba(239, 68, 68, 0.3);
}

.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-color);
  min-width: 0; /* 关键：允许flex子元素缩小 */
  overflow: hidden; /* 防止内容溢出 */
}

.chat-header {
  padding: 1.25rem 1.5rem;
  min-height: 80px;
  background-color: var(--header-bg, var(--card-bg));
  border-bottom: 1px solid var(--border-subtle, var(--border-color));
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

.sidebar-toggle-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 50%;
  transition: background-color 0.2s ease, transform 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  color: var(--text-primary);
  flex-shrink: 0;
  position: absolute;
  left: 1rem;
  z-index: 10;
  will-change: transform;
}

.sidebar-toggle-btn:hover {
  background-color: var(--hover-color);
  transform: scale3d(1.1, 1.1, 1);
}

.header-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  animation: fadeInUp 0.4s ease-out;
  will-change: transform, opacity;
  position: relative;
  padding-left: 80px; /* 为小人留出空间 */
}

.anime-character {
  position: absolute;
  left: 600px;
  top: 50%;
  transform: translateY(-50%);
  width: 70px;
  height: 70px;
  z-index: 10;
  cursor: pointer;
  user-select: none;
}

.character-container {
  position: relative;
  width: 100%;
  height: 100%;
  animation: characterFloat 3s ease-in-out infinite, characterWiggle 2.5s ease-in-out infinite, characterHeartbeat 2s ease-in-out infinite;
  transform-origin: center center;
}

.anime-character:hover .character-container {
  animation: characterFloat 1s ease-in-out infinite, characterWiggle 1s ease-in-out infinite, characterHeartbeat 1s ease-in-out infinite, characterWave 0.5s ease-in-out infinite;
  transform: scale(1.2);
}

.anime-character:active .character-container {
  animation-play-state: paused;
  transform: scale(0.9);
}

.character-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  filter: drop-shadow(0 4px 12px rgba(59, 130, 246, 0.3));
  animation: characterBlink 3s ease-in-out infinite, characterGlow 2s ease-in-out infinite;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%);
}

@keyframes characterFloat {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-12px);
  }
}

@keyframes characterWiggle {
  0%, 100% {
    transform: rotate(0deg);
  }
  20% {
    transform: rotate(-8deg);
  }
  40% {
    transform: rotate(8deg);
  }
  60% {
    transform: rotate(-5deg);
  }
  80% {
    transform: rotate(5deg);
  }
}

@keyframes characterHeartbeat {
  0%, 100% {
    transform: scale(1);
  }
  10%, 30% {
    transform: scale(1.05);
  }
  20%, 40% {
    transform: scale(1);
  }
}

@keyframes characterWave {
  0%, 100% {
    transform: rotate(0deg);
  }
  25% {
    transform: rotate(-15deg);
  }
  75% {
    transform: rotate(15deg);
  }
}

@keyframes characterBlink {
  0%, 85%, 100% {
    opacity: 1;
  }
  87%, 93% {
    opacity: 0.1;
  }
}

@keyframes characterGlow {
  0%, 100% {
    filter: drop-shadow(0 4px 12px rgba(59, 130, 246, 0.3));
  }
  50% {
    filter: drop-shadow(0 4px 20px rgba(59, 130, 246, 0.5));
  }
}

/* 星星闪烁效果 */
.sparkle {
  position: absolute;
  font-size: 12px;
  pointer-events: none;
  animation: sparkleFloat 3s ease-in-out infinite;
}

.sparkle-1 {
  top: -10px;
  left: 20%;
  animation-delay: 0s;
}

.sparkle-2 {
  top: 10px;
  right: 15%;
  animation-delay: 1s;
}

.sparkle-3 {
  bottom: -5px;
  left: 50%;
  animation-delay: 2s;
}

@keyframes sparkleFloat {
  0%, 100% {
    opacity: 0;
    transform: translateY(0) scale(0.5);
  }
  50% {
    opacity: 1;
    transform: translateY(-15px) scale(1);
  }
}

.character-bubble {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: 10px;
  padding: 0.5rem 0.75rem;
  background: var(--primary-color);
  color: white;
  border-radius: 12px;
  font-size: 0.75rem;
  white-space: nowrap;
  animation: bubblePop 0.3s ease-out, bubbleFade 2s ease-out 0.3s forwards;
  box-shadow: 0 4px 12px rgba(129, 140, 248, 0.4);
  z-index: 10;
  pointer-events: none;
}

.character-bubble::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: var(--primary-color);
}

@keyframes bubblePop {
  from {
    opacity: 0;
    transform: translateX(-50%) scale(0.5);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) scale(1);
  }
}

@keyframes bubbleFade {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
    transform: translateX(-50%) translateY(-10px);
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translate3d(0, 10px, 0);
  }
  to {
    opacity: 1;
    transform: translate3d(0, 0, 0);
  }
}

.header-title {
  color: var(--primary-color);
  margin: 0;
  font-size: 2rem;
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
  animation: fadeInUp 0.4s ease-out 0.05s both;
  will-change: transform, opacity;
}

.title-main {
  font-weight: 700;
  letter-spacing: -0.02em;
}

.subtitle-cn {
  font-size: 1.1rem;
  color: var(--text-secondary);
  font-weight: 400;
  font-style: italic;
  opacity: 0.9;
}

.header-desc {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0;
  font-weight: 400;
  margin-bottom: 0.75rem;
  animation: fadeInUp 0.4s ease-out 0.1s both;
  letter-spacing: 0.01em;
  will-change: transform, opacity;
}

.header-session {
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-weight: 500;
  margin: 0;
  padding: 0.25rem 0.75rem;
  background-color: var(--bg-secondary);
  border-radius: 12px;
  display: inline-block;
  animation: fadeInUp 0.4s ease-out 0.15s both;
  transition: background-color 0.2s ease, transform 0.2s ease;
  will-change: transform, opacity;
}

.header-session:hover {
  background-color: var(--hover-color);
  transform: translate3d(0, -1px, 0);
}

.messages-container {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  min-width: 0; /* 关键：允许flex子元素缩小 */
  max-width: 100%; /* 限制最大宽度为父容器的100% */
  /* 优化滚动性能 */
  -webkit-overflow-scrolling: touch;
  scroll-behavior: smooth;
  contain: layout style paint;
}

.empty-state {
  margin: auto;
  color: var(--text-secondary);
  text-align: center;
  padding: 2rem;
  max-width: 600px;
}

.welcome-content h3 {
  color: var(--primary-color);
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
}

.welcome-content .subtitle {
  font-size: 1rem;
  margin-bottom: 0.5rem;
  color: var(--text-secondary);
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin: 2rem 0;
  max-width: 800px;
  width: 100%;
}

.feature-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  background-color: var(--card-bg);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  transition: all 0.3s ease;
  cursor: default;
}

.feature-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow);
  border-color: var(--primary-color);
}

.feature-icon {
  font-size: 2rem;
  line-height: 1;
  flex-shrink: 0;
}

.feature-text {
  flex: 1;
}

.feature-title {
  font-weight: 600;
  font-size: 1rem;
  color: var(--text-primary);
  margin-bottom: 0.25rem;
}

.feature-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.example-queries {
  margin: 2rem 0;
  padding: 1.5rem;
  background-color: var(--card-bg);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  max-width: 600px;
  width: 100%;
}

.example-title {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-bottom: 1rem;
  font-weight: 500;
}

.query-examples {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.example-query {
  padding: 0.75rem 1rem;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 0.9rem;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: 'JetBrains Mono', monospace;
}

.example-query:hover {
  background-color: var(--hover-color);
  border-color: var(--primary-color);
  transform: translateX(4px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.example-query:active {
  transform: translateX(2px);
}

.start-hint {
  font-size: 0.9rem;
  color: var(--text-secondary);
  margin-top: 1.5rem;
  font-style: italic;
}

/* 定价卡片模态框样式 */
.pricing-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.3s ease;
  backdrop-filter: blur(4px);
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.pricing-card {
  position: relative;
  width: 100%;
  max-width: 420px;
  padding: 4px;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  border-radius: 12px;
  animation: slideUp 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.close-btn {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  width: 36px;
  height: 36px;
  z-index: 20;
  backdrop-filter: blur(4px);
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: rotate(90deg);
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.pricing-badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  padding: 0.5rem 1.25rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 700;
  color: white;
  text-transform: uppercase;
  font-style: italic;
  letter-spacing: 0.5px;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  border: 1px solid rgba(59, 130, 246, 0.3);
  z-index: 10;
}

.badge-icon {
  font-size: 0.875rem;
}

.pricing-content {
  background: #1e293b;
  border-radius: 16px;
  padding: 2rem;
  color: white;
}

.plan-name {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 1rem 0;
  color: white;
  font-family: 'Inter', sans-serif;
}

.price-section {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.price {
  font-size: 2.5rem;
  font-weight: 700;
  color: white;
  font-family: 'Inter', sans-serif;
}

.price-period {
  font-size: 1rem;
  color: #94a3b8;
  font-weight: 400;
}

.plan-description {
  font-size: 0.95rem;
  color: #cbd5e1;
  margin: 0 0 1.5rem 0;
  line-height: 1.6;
  font-family: 'Inter', sans-serif;
}

.signup-btn {
  width: 100%;
  padding: 0.875rem 1.5rem;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 8px;
  color: white;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: 'Inter', sans-serif;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.signup-btn:hover {
  background: linear-gradient(135deg, var(--primary-light) 0%, var(--primary-color) 100%);
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.3);
  border-color: rgba(59, 130, 246, 0.5);
}

.signup-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 1rem auto;
  color: var(--text-secondary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  position: absolute;
  right: 1rem;
  z-index: 10;
}

.plus-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 8px;
  color: white;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
  will-change: transform;
}

.plus-btn:hover {
  background: linear-gradient(135deg, var(--primary-light) 0%, var(--primary-color) 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  border-color: rgba(59, 130, 246, 0.5);
}

.plus-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
}

.plus-icon {
  font-size: 1rem;
  line-height: 1;
}

.plus-text {
  font-family: 'Inter', sans-serif;
}

.settings-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 50%;
  transition: background-color 0.2s ease, transform 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  color: var(--text-primary);
  flex-shrink: 0;
  will-change: transform;
}

.settings-btn:hover {
  background-color: var(--hover-color);
  transform: scale3d(1.1, 1.1, 1) rotate(90deg);
}
</style>

import { defineStore } from 'pinia';

export const useStore = defineStore('main', {
  state: () => ({
    apiKey: localStorage.getItem('apiKey') || null,
    currentSession: localStorage.getItem('currentSession') || 'default_session',
    sessions: JSON.parse(localStorage.getItem('sessions') || '["default_session"]'),
    messages: {},
    loading: false,
    error: null,
    currentModel: localStorage.getItem('currentModel') || '',
    models: [],
    sessionFiles: (() => {
      try {
        return JSON.parse(localStorage.getItem('sessionFiles') || '{}') || {};
      } catch (err) {
        console.error('Failed to parse sessionFiles from localStorage', err);
        return {};
      }
    })()
  }),
  
  actions: {
    // 保存API Key
    setApiKey(key) {
      this.apiKey = key;
      localStorage.setItem('apiKey', key);
    },
    
    // 清除API Key（退出登录）
    clearApiKey() {
      this.apiKey = null;
      localStorage.removeItem('apiKey');
    },
    
    // 添加新会话
    addSession(sessionId) {
      if (!this.sessions.includes(sessionId)) {
        this.sessions.push(sessionId);
        localStorage.setItem('sessions', JSON.stringify(this.sessions));
      }
      this.setCurrentSession(sessionId);
    },
    
    // 设置当前会话
    setCurrentSession(sessionId) {
      this.currentSession = sessionId;
      localStorage.setItem('currentSession', sessionId);
    },
    
    // 删除会话
    removeSession(sessionId) {
      this.sessions = this.sessions.filter(id => id !== sessionId);
      localStorage.setItem('sessions', JSON.stringify(this.sessions));
      
      // 如果删除的是当前会话，切换到默认会话
      if (sessionId === this.currentSession) {
        const newSession = this.sessions.length > 0 ? this.sessions[0] : 'default_session';
        this.setCurrentSession(newSession);
      }

      if (this.sessionFiles[sessionId]) {
        delete this.sessionFiles[sessionId];
        localStorage.setItem('sessionFiles', JSON.stringify(this.sessionFiles));
      }
    },
    
    // 保存消息到状态
    addMessage(sessionId, isUser, content, messageId = null) {
      if (!this.messages[sessionId]) {
        this.messages[sessionId] = [];
      }
      
      this.messages[sessionId].push({
        id: messageId || Date.now(),
        isUser,
        content,
        timestamp: new Date()
      });
    },
    
    // 更新消息内容（用于流式更新）
    updateMessage(sessionId, messageId, content) {
      if (!this.messages[sessionId]) return;
      
      const message = this.messages[sessionId].find(msg => msg.id === messageId);
      if (message) {
        message.content = content;
      }
    },
    
    // 从历史记录加载消息
    loadHistory(sessionId, history) {
      // 确保会话消息数组存在
      if (!this.messages[sessionId]) {
        this.messages[sessionId] = [];
      }
      
      // 如果有历史记录，先清空再加载
      if (history) {
        this.messages[sessionId] = [];
      } else {
        // 没有历史记录，确保是空数组
        this.messages[sessionId] = [];
        return;
      }
      
      const lines = history.split('\n');
      let currentMessage = null;
      
      lines.forEach(line => {
        if (line.startsWith('用户：')) {
          // 保存上一条消息
          if (currentMessage) {
            this.addMessage(sessionId, currentMessage.isUser, currentMessage.content);
          }
          // 开始新的用户消息
          currentMessage = {
            isUser: true,
            content: line.replace('用户：', '').trim()
          };
        } else if (line.startsWith('回复：')) {
          // 保存上一条消息
          if (currentMessage) {
            this.addMessage(sessionId, currentMessage.isUser, currentMessage.content);
          }
          // 开始新的AI回复
          currentMessage = {
            isUser: false,
            content: line.replace('回复：', '').trim()
          };
        } else if (line.startsWith('---')) {
          // 分隔线，跳过
          return;
        } else if (currentMessage && line.trim()) {
          // 多行内容，追加到当前消息
          currentMessage.content += '\n' + line;
        }
      });
      
      // 保存最后一条消息
      if (currentMessage) {
        this.addMessage(sessionId, currentMessage.isUser, currentMessage.content);
      }
    },
    
    // 清空会话消息
    clearSessionMessages(sessionId) {
      // 使用 Vue 的响应式方式更新
      if (this.messages[sessionId]) {
        this.messages[sessionId] = [];
      } else {
        // 如果不存在，创建空数组
        this.messages = { ...this.messages, [sessionId]: [] };
      }

      if (this.sessionFiles[sessionId]) {
        delete this.sessionFiles[sessionId];
        localStorage.setItem('sessionFiles', JSON.stringify(this.sessionFiles));
      }
    },
    
    // 设置加载状态
    setLoading(state) {
      this.loading = state;
    },
    
    // 设置错误信息
    setError(message) {
      this.error = message;
      // 3秒后自动清除错误信息
      setTimeout(() => {
        this.error = null;
      }, 3000);
    },

    // 保存模型列表
    setModelOptions(options) {
      this.models = options || [];
    },

    // 更新当前模型
    setCurrentModel(modelKey) {
      this.currentModel = modelKey;
      if (modelKey) {
        localStorage.setItem('currentModel', modelKey);
      } else {
        localStorage.removeItem('currentModel');
      }
    },

    addUploadedFile(sessionId, fileMeta) {
      if (!sessionId || !fileMeta || !fileMeta.path) return;

      if (!this.sessionFiles[sessionId]) {
        this.sessionFiles[sessionId] = [];
      }

      const exists = this.sessionFiles[sessionId].some(
        (item) => item.path === fileMeta.path
      );

      if (!exists) {
        this.sessionFiles[sessionId].push({
          name: fileMeta.name || fileMeta.path,
          path: fileMeta.path,
          stored: fileMeta.stored || null,
        });
        localStorage.setItem('sessionFiles', JSON.stringify(this.sessionFiles));
      }
    },

    getSessionFiles(sessionId) {
      return this.sessionFiles[sessionId] || [];
    },

    clearSessionFiles(sessionId) {
      if (this.sessionFiles[sessionId]) {
        delete this.sessionFiles[sessionId];
        localStorage.setItem('sessionFiles', JSON.stringify(this.sessionFiles));
      }
    }
  }
});

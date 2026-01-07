import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器添加token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('apiKey');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器处理错误
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // 未授权，清除token并跳转到登录页
      localStorage.removeItem('apiKey');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default {
  // 登录
  login(username, password) {
    return api.post('/login', { username, password });
  },
  
  // 发送聊天消息
  chat(sessionId, userInput, queryType = "analysis") {
    return api.post('/chat', { session_id: sessionId, user_input: userInput, query_type: queryType });
  },
  
  // 流式聊天消息
  async chatStream(sessionId, userInput, queryType = "general_chat", signal, onMessage, onError, onComplete) {
    const token = localStorage.getItem('apiKey');
    const baseURL = window.location.origin;
    
    try {
      const response = await fetch(`${baseURL}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          session_id: sessionId,
          user_input: userInput,
          query_type: queryType,
        }),
        signal: signal,  // 添加取消信号
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // 保留最后一个不完整的行

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              try {
                const parsed = JSON.parse(data);
                if (parsed.error) {
                  onError(parsed.error);
                  return;
                }
                if (parsed.done) {
                  onComplete(parsed.content);
                  return;
                }
                if (parsed.delta) {
                  onMessage(parsed.content);
                }
              } catch (e) {
                console.error('解析 SSE 数据失败:', e);
              }
            }
          }
        }
      } catch (readError) {
        // 如果是 AbortError，说明用户主动停止
        if (readError.name === 'AbortError') {
          console.log('用户停止了生成');
          reader.cancel();  // 取消读取
          return;
        }
        throw readError;
      } finally {
        reader.releaseLock();
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        onError('AbortError');  // 特殊标记，前端会忽略
      } else {
        onError(error.message || '网络错误');
      }
    }
  },
  
  // 获取历史记录
  getHistory(sessionId) {
    return api.get('/history', { params: { session_id: sessionId } });
  },
  
  // 清空历史记录
  clearHistory(sessionId) {
    return api.delete('/history', { params: { session_id: sessionId } });
  },

  // 获取可用模型配置
  getModels() {
    return api.get('/models');
  },

  // 切换当前模型
  switchModel(modelKey) {
    return api.post('/models/switch', { model_key: modelKey });
  },

  // 上传文件
  uploadFile(formData, config = {}) {
    return api.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      ...config,
    });
  },
};

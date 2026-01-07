<template>
  <div class="message" :class="{ 'user-message': isUser }">
    <div class="message-avatar">
      <div :class="isUser ? 'user-avatar' : 'bot-avatar'">
        {{ isUser ? '用户' : 'AI' }}
      </div>
    </div>
    <div class="message-content">
      <div class="message-text" v-if="isUser">{{ content }}</div>
      <div class="message-text markdown-body" v-else v-html="renderedMarkdown"></div>
      <div class="message-time">
        {{ formatTime(timestamp) }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, computed } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

const props = defineProps({
  isUser: {
    type: Boolean,
    required: true
  },
  content: {
    type: String,
    required: true
  },
  timestamp: {
    type: Date,
    required: true
  }
});

// 配置 marked 选项
marked.setOptions({
  breaks: true,  // 支持换行
  gfm: true,     // 启用 GitHub Flavored Markdown
  headerIds: false,
  mangle: false
});

// 缓存渲染结果，避免重复计算
let cachedContent = '';
let cachedHtml = '';

// 渲染 Markdown（仅用于 AI 回复）
const renderedMarkdown = computed(() => {
  if (!props.content) return '';
  
  // 如果内容没有变化，直接返回缓存
  if (props.content === cachedContent && cachedHtml) {
    return cachedHtml;
  }
  
  const html = marked(props.content);
  // 使用 DOMPurify 防止 XSS 攻击
  const sanitized = DOMPurify.sanitize(html);
  
  // 更新缓存
  cachedContent = props.content;
  cachedHtml = sanitized;
  
  return sanitized;
});

const formatTime = (date) => {
  return new Date(date).toLocaleTimeString();
};
</script>

<style scoped>
.message {
  display: flex;
  margin-bottom: 1rem;
  max-width: 80%;
  min-width: 0; /* 允许flex子元素缩小 */
  width: fit-content; /* 根据内容自适应宽度 */
  /* 优化渲染性能 */
  contain: layout style;
  will-change: transform;
}

.message.user-message {
  margin-left: auto;
  flex-direction: row-reverse;
}

.message-avatar {
  margin-right: 0.5rem;
}

.user-message .message-avatar {
  margin-right: 0;
  margin-left: 0.5rem;
}

.user-avatar, .bot-avatar {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  font-weight: bold;
  font-size: 0.875rem;
}

.user-avatar {
  background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
  color: white;
  border: 2px solid rgba(59, 130, 246, 0.3);
}

.bot-avatar {
  background: linear-gradient(135deg, var(--secondary-color) 0%, #0891b2 100%);
  color: white;
  border: 2px solid rgba(6, 182, 212, 0.3);
}

.message-content {
  padding: 0.75rem 1rem;
  border-radius: var(--radius);
  position: relative;
  min-width: 0; /* 允许内容缩小 */
  max-width: 100%; /* 严格限制最大宽度 */
  overflow: hidden; /* 防止内容溢出 */
  word-wrap: break-word; /* 长单词自动换行 */
  overflow-wrap: break-word; /* 长单词自动换行 */
  box-sizing: border-box; /* 确保padding计算在内 */
}

.message:not(.user-message) .message-content {
  background-color: var(--bot-message);
  color: var(--text-primary);
}

.user-message .message-content {
  background-color: var(--user-message);
  color: white;
}

.user-message .message-time {
  color: rgba(255, 255, 255, 0.7);
}

.message-text {
  margin-bottom: 0.25rem;
  line-height: 1.5;
}

.message-time {
  font-size: 0.625rem;  /* 10px */
  color: var(--text-tertiary, #64748b);
  text-align: right;
  margin-top: 0.25rem;
  opacity: 0.8;
}

/* Markdown 样式 */
.markdown-body {
  line-height: 1.6;
  word-wrap: break-word;
  overflow-wrap: break-word;
  max-width: 100%; /* 限制最大宽度 */
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: 600;
}

.markdown-body :deep(h1) { font-size: 1.5em; }
.markdown-body :deep(h2) { font-size: 1.3em; }
.markdown-body :deep(h3) { font-size: 1.1em; }

.markdown-body :deep(p) {
  margin-bottom: 0.5em;
}

.markdown-body :deep(code) {
  background-color: var(--code-bg, rgba(175, 184, 193, 0.2));
  color: var(--code-color, #e01e5a);
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: 'JetBrains Mono', 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
  font-weight: 500;
}

.markdown-body :deep(pre) {
  background-color: var(--code-block-bg, #f6f8fa);
  border-radius: 6px;
  padding: 1em;
  overflow-x: auto; /* 横向滚动 */
  overflow-y: hidden; /* 隐藏纵向滚动 */
  margin: 0.5em 0;
  border: 1px solid var(--border-color);
  max-width: 100%; /* 限制最大宽度 */
  white-space: pre; /* 保持代码格式 */
}

.markdown-body :deep(pre code) {
  background-color: transparent;
  color: var(--code-block-color, #24292e);
  padding: 0;
  font-size: 0.85em;
  line-height: 1.45;
  white-space: pre; /* 保持代码格式，不自动换行 */
  word-wrap: normal; /* 不自动换行 */
  overflow-wrap: normal; /* 不自动换行 */
}

.markdown-body :deep(blockquote) {
  border-left: 4px solid var(--border-color);
  padding-left: 1em;
  margin: 0.5em 0;
  color: var(--text-secondary);
  background-color: var(--bg-secondary, rgba(0, 0, 0, 0.05));
  padding: 0.5em 1em;
  border-radius: 4px;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 2em;
  margin: 0.5em 0;
}

.markdown-body :deep(li) {
  margin: 0.25em 0;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.5em 0;
  display: block; /* 允许表格滚动 */
  overflow-x: auto; /* 横向滚动 */
  max-width: 100%; /* 限制最大宽度 */
}

.markdown-body :deep(table th),
.markdown-body :deep(table td) {
  border: 1px solid var(--border-color);
  padding: 0.5em;
  white-space: nowrap; /* 表格单元格不换行 */
}

.markdown-body :deep(table th) {
  background-color: var(--bg-secondary);
  font-weight: 600;
}

.markdown-body :deep(a) {
  color: var(--primary-color);
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
  color: var(--primary-light);
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--border-color);
  margin: 1em 0;
}

.markdown-body :deep(strong) {
  font-weight: 600;
}

.markdown-body :deep(em) {
  font-style: italic;
}

/* 自定义滚动条样式（用于代码块和表格） */
.markdown-body :deep(pre)::-webkit-scrollbar,
.markdown-body :deep(table)::-webkit-scrollbar {
  height: 8px;
}

.markdown-body :deep(pre)::-webkit-scrollbar-track,
.markdown-body :deep(table)::-webkit-scrollbar-track {
  background: var(--bg-secondary);
  border-radius: 4px;
}

.markdown-body :deep(pre)::-webkit-scrollbar-thumb,
.markdown-body :deep(table)::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 4px;
}

.markdown-body :deep(pre)::-webkit-scrollbar-thumb:hover,
.markdown-body :deep(table)::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary);
}
</style>

<!-- src/App.vue -->
<script setup>
import { ref, onMounted } from 'vue';

// 定义响应式变量
const question = ref('');
const answer = ref('');
const loading = ref(false);
const error = ref('');
const conversationHistory = ref([]); // 存储对话历史
const sessionId = ref('');
const sessions = ref([]);

const API_BASE_URL = 'http://localhost:8001';
const SESSION_KEY = 'agent_session_id';
const SESSIONS_KEY = 'agent_sessions_list';

const saveSessions = () => {
  localStorage.setItem(SESSION_KEY, sessionId.value);
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions.value));
};

const loadSessions = () => {
  try {
    const savedSessions = localStorage.getItem(SESSIONS_KEY);
    if (savedSessions) {
      const parsedSessions = JSON.parse(savedSessions);
      // 为旧会话数据添加缺失的字段
      sessions.value = parsedSessions.map(session => ({
        id: session.id,
        name: session.name,
        lastMessage: session.lastMessage || '',
        createdAt: session.createdAt || new Date(parseInt(session.id)).toLocaleString('zh-CN'),
        updatedAt: session.updatedAt || new Date(parseInt(session.id)).toLocaleString('zh-CN'),
      }));
    }
  } catch (err) {
    console.warn('读取会话列表失败:', err);
  }
};

const setSession = (id) => {
  sessionId.value = id;
  localStorage.setItem(SESSION_KEY, id);
};

const createNewSession = async () => {
  const newId = Date.now().toString();
  const now = new Date();
  const newSession = {
    id: newId,
    name: `会话 ${sessions.value.length + 1}`,
    lastMessage: '',
    createdAt: now.toLocaleString('zh-CN'),
    updatedAt: now.toLocaleString('zh-CN'),
  };
  sessions.value.unshift(newSession);
  setSession(newId);
  saveSessions();
  conversationHistory.value = [];
  answer.value = '';
  error.value = '';
};

const selectSession = async (id) => {
  if (!id || sessionId.value === id) {
    return;
  }
  setSession(id);
  await loadSessionHistory(id);
  saveSessions();
};

const loadSessionHistory = async (id) => {
  try {
    const response = await fetch(`${API_BASE_URL}/history/${id}`);
    if (!response.ok) {
      console.warn('获取历史失败:', response.status);
      conversationHistory.value = [];
      return;
    }
    const data = await response.json();
    if (Array.isArray(data.history)) {
      conversationHistory.value = data.history.map((item) => ({
        type: item.role === 'assistant' ? 'ai' : item.role,
        content: item.content,
      }));
      
      // 更新会话的最后消息预览
      const currentSession = sessions.value.find(s => s.id === id);
      if (currentSession && data.history.length > 0) {
        const lastMessage = data.history[data.history.length - 1];
        currentSession.lastMessage = lastMessage.content.length > 30 ? lastMessage.content.substring(0, 30) + '...' : lastMessage.content;
      }
    } else {
      conversationHistory.value = [];
    }
  } catch (err) {
    console.warn('加载历史会话失败:', err);
    conversationHistory.value = [];
  }
};

const ensureSession = async () => {
  loadSessions();
  const savedId = localStorage.getItem(SESSION_KEY);
  if (savedId && sessions.value.some((session) => session.id === savedId)) {
    await selectSession(savedId);
    return;
  }
  await createNewSession();
};

/**
 * 发送问题到后端 API
 */
const sendQuestion = async () => {
  if (!question.value.trim()) {
    alert('请输入问题');
    return;
  }

  if (!sessionId.value) {
    await createNewSession();
  }

  const userQuestion = question.value.trim();
  conversationHistory.value.push({ type: 'user', content: userQuestion });
  question.value = '';
  answer.value = '';
  error.value = '';
  loading.value = true;

  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: userQuestion,
        session_id: sessionId.value,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    conversationHistory.value.push({ type: 'ai', content: data.answer });
    
    // 更新会话的最后消息预览
    const currentSession = sessions.value.find(s => s.id === sessionId.value);
    if (currentSession) {
      currentSession.lastMessage = data.answer.length > 30 ? data.answer.substring(0, 30) + '...' : data.answer;
      currentSession.updatedAt = new Date().toLocaleString('zh-CN');
    }
    
    saveSessions();
  } catch (err) {
    console.error('API 调用失败:', err);
    error.value = `请求失败: ${err.message}`;
    conversationHistory.value.push({ type: 'error', content: err.message });
  } finally {
    loading.value = false;
  }
};

const deleteSession = async (id, event) => {
  event.stopPropagation(); // 阻止事件冒泡，避免触发selectSession
  if (!confirm('确定要删除这个会话吗？')) {
    return;
  }

  try {
    // 调用后端API删除历史
    const response = await fetch(`${API_BASE_URL}/history/${id}/reset`, {
      method: 'POST',
    });

    if (!response.ok) {
      throw new Error(`删除失败: ${response.status}`);
    }

    // 从本地会话列表中移除
    sessions.value = sessions.value.filter(session => session.id !== id);

    // 如果删除的是当前会话，切换到第一个会话或创建新会话
    if (sessionId.value === id) {
      if (sessions.value.length > 0) {
        await selectSession(sessions.value[0].id);
      } else {
        await createNewSession();
      }
    }

    saveSessions();
  } catch (err) {
    console.error('删除会话失败:', err);
    alert(`删除会话失败: ${err.message}`);
  }
};

const getMessageClass = (type) => {
  switch (type) {
    case 'user':
      return 'message-user';
    case 'ai':
      return 'message-ai';
    case 'error':
      return 'message-error';
    default:
      return '';
  }
};

onMounted(() => {
  ensureSession();
});
</script>

<template>
  <div class="app-container">
    <header class="header">
      <h1>AI 问答助手</h1>
    </header>

    <div class="body-content">
      <aside class="sidebar">
        <div class="sidebar-header">
          <h2>会话管理</h2>
          <button class="sidebar-btn" @click="createNewSession">新增会话</button>
        </div>

        <div class="session-list">
          <div
            v-for="session in sessions"
            :key="session.id"
            class="session-item"
            :class="{ active: session.id === sessionId }"
            @click="selectSession(session.id)"
          >
            <div class="session-content">
              <div class="session-name">{{ session.name }}</div>
              <div class="session-preview">
                {{ session.lastMessage || `创建于 ${session.createdAt}` }}
              </div>
            </div>
            <button
              class="delete-btn"
              @click="deleteSession(session.id, $event)"
              title="删除会话"
            >
              ×
            </button>
          </div>

          <div v-if="sessions.length === 0" class="session-empty">
            尚无会话，请点击“新增会话”。
          </div>
        </div>
      </aside>

      <main class="main-content">
        <!-- 对话历史区域 -->
        <div class="conversation-history">
          <div
            v-for="(item, index) in conversationHistory"
            :key="index"
            :class="['message-item', getMessageClass(item.type)]"
          >
            <div class="message-bubble">
              <span>{{ item.content }}</span>
            </div>
          </div>

          <!-- 加载指示器 -->
          <div v-if="loading" class="message-item message-loading">
            <div class="message-bubble">
              <span>AI 正在思考...</span>
              <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="input-section">
          <textarea
            v-model="question"
            placeholder="请输入您的问题..."
            :disabled="loading"
            @keydown="handleKeyDown"
            rows="2"
            class="input-textarea"
          ></textarea>
          <button @click="sendQuestion" :disabled="loading" class="submit-btn">
            <span v-if="!loading">发送</span>
            <span v-else>...</span>
          </button>
        </div>

        <!-- 全局错误信息 (可选，也可以只在历史中显示) -->
        <div v-if="error" class="global-error">
          {{ error }}
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
/* === 强制全局宽度扩展 === */
html, body {
  width: 100%;
  min-width: 100vw; /* 关键：防止被压缩 */
  overflow-x: hidden;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  background-color: #f5f7fa;
  /* 移除可能的宽度限制 */
  max-width: none !important;
  width: 100% !important;
}


.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  box-shadow: 0 0 18px rgba(0, 0, 0, 0.08);
  background-color: white;
  min-width: 900px;
}

/* 头部 */
.header {
  background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
  color: white;
  text-align: center;
  padding: 20px 10px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.header h1 {
  margin: 0;
  font-size: 1.8rem;
  font-weight: 600;
}

.body-content {
  display: flex;
  gap: 20px;
  padding: 20px;
  flex: 1;
}

.sidebar {
  width: 280px;
  border-right: 1px solid #e9ecef;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-right: 10px;
}

.sidebar-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 1.1rem;
  color: #1f2a44;
}

.sidebar-btn {
  padding: 10px 14px;
  background: #2575fc;
  border: none;
  border-radius: 12px;
  color: white;
  cursor: pointer;
  font-weight: 600;
}

.session-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.session-item {
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid #edf2f7;
  background-color: #fafbff;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  display: flex;
  align-items: flex-start;
}

.session-item.active {
  background-color: #eef2ff;
  border-color: #c7d2fe;
}

.session-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.06);
}

.session-content {
  flex: 1;
  min-width: 0; /* 防止内容被压缩 */
  padding-right: 30px; /* 为删除按钮留空间 */
}

.session-name {
  color: #1f2a44;
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}

.session-preview {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delete-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: none;
  border: none;
  color: #dc3545;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 50%;
  transition: all 0.2s;
  opacity: 0.6;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.delete-btn:hover {
  opacity: 1;
  background-color: rgba(220, 53, 69, 0.15);
  transform: scale(1.1);
}

.session-empty {
  padding: 16px;
  border-radius: 14px;
  background: #f8fafc;
  color: #475569;
  line-height: 1.6;
}

.main-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  height: calc(100vh - 120px);
  padding: 10px 0;
  gap: 20px;
}

/* 对话历史区域 */
.conversation-history {
  flex-grow: 1;
  overflow-y: auto;
  padding-right: 10px;
  display: flex;
  flex-direction: column;
  gap: 15px;
  width: 100%; /* 确保占满容器 */
}

.message-item {
  display: flex;
  animation: fadeInUp 0.3s ease-out forwards;
}

.message-item.message-user {
  justify-content: flex-end;
}

.message-item.message-ai,
.message-item.message-error,
.message-item.message-loading {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 18px;
  line-height: 1.5;
  word-wrap: break-word;
  position: relative;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  transition: all 0.2s ease;
}

.message-user .message-bubble {
  background-color: #007bff;
  color: white;
  border-bottom-right-radius: 4px;
}

.message-ai .message-bubble {
  background-color: #e9ecef;
  color: #333;
  border-bottom-left-radius: 4px;
}

/* 输入区域 */
.input-section {
  display: flex;
  gap: 10px;
  padding-top: 10px;
  border-top: 1px solid #eee;
  width: 100%;
}

.input-textarea {
  flex-grow: 1;
  padding: 12px 15px;
  border: 1px solid #ddd;
  border-radius: 20px;
  resize: none;
  font-size: 16px;
  outline: none;
  transition: border-color 0.2s;
  min-width: 0; /* 防止被压缩 */
}

.submit-btn {
  padding: 0 20px;
  background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
  color: white;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: opacity 0.2s;
  flex-shrink: 0; /* 防止按钮被压缩 */
}

/* 全局错误信息 */
.global-error {
  color: #dc3545;
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  padding: 10px 15px;
  border-radius: 4px;
  text-align: center;
  margin-top: 10px;
  width: 100%;
}

/* 动画 & 打字效果保持不变 */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.typing-indicator {
  display: flex;
  justify-content: center;
  margin-top: 8px;
}
.typing-indicator span {
  width: 8px; height: 8px; background-color: #666; border-radius: 50%; margin: 0 3px;
  animation: typing 1s infinite;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

/* 滚动条样式 */
.conversation-history::-webkit-scrollbar {
  width: 6px;
}
.conversation-history::-webkit-scrollbar-thumb {
  background-color: rgba(0,0,0,0.2);
  border-radius: 3px;
}
.conversation-history::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0,0,0,0.3);
}
</style>
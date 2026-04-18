<!-- src/App.vue -->
<script setup>
import { ref } from 'vue';

// 定义响应式变量
const question = ref('');
const answer = ref('');
const loading = ref(false);
const error = ref('');
const conversationHistory = ref([]); // 存储对话历史

// API 请求地址，如果后端不在 localhost:8000，请修改此处
const API_BASE_URL = 'http://localhost:8000'; 

/**
 * 发送问题到后端 API
 */
const sendQuestion = async () => {
  if (!question.value.trim()) {
    // 可以用一个更优雅的方式提示，比如 Toast
    alert('请输入问题');
    return;
  }

  const userQuestion = question.value.trim();
  // 添加用户问题到历史记录
  conversationHistory.value.push({ type: 'user', content: userQuestion });
  
  // 清空当前输入和之前的答案/错误
  question.value = '';
  answer.value = '';
  error.value = '';
  loading.value = true;

  try {
    const sessionId = localStorage.getItem('sessionId') || Date.now().toString();
    localStorage.setItem('sessionId', sessionId); // 保存会话ID

    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        question: userQuestion,
        session_id: sessionId  // 传递会话ID
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    // 将 AI 回答添加到历史记录
    conversationHistory.value.push({ type: 'ai', content: data.answer });
  } catch (err) {
    console.error('API 调用失败:', err);
    error.value = `请求失败: ${err.message}`;
    // 也可以将错误信息加入历史记录
    conversationHistory.value.push({ type: 'error', content: err.message });
  } finally {
    loading.value = false;
  }
};

/**
 * 按 Enter 键发送问题
 */
const handleKeyDown = (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault(); // 阻止换行
    sendQuestion();
  }
};

/**
 * 获取消息项的 CSS 类名
 */
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
</script>

<template>
  <div class="app-container">
    <header class="header">
      <h1>AI 问答助手</h1>
    </header>
    
    <main class="main-content">
      <!-- 对话历史区域 -->
      <div class="conversation-history">
        <div 
          v-for="(item, index) in conversationHistory" 
          :key="index" 
          :class="['message-item', getMessageClass(item.type)]"
        >
          <div class="message-bubble">
            <!-- <strong v-if="item.type !== 'ai'">{{ item.type === 'user' ? '你' : '系统' }}:</strong> -->
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
  /* 关键：不再用 max-width，而是用 width + margin auto 居中 */
  width: 90%; /* 在大屏上占 90% 宽度，小屏自适应 */
  max-width: 1400px; /* 大屏上限 */
  margin: 0 auto;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
  background-color: white;
  /* 确保不被压缩 */
  min-width: 800px; /* 强制最小宽度，避免过窄 */
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

/* 主内容区 */
.main-content {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  padding: 20px;
  gap: 20px;
  /* 关键：让内容区域也撑开 */
  width: 100%;
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
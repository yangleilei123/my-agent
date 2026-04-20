from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import create_agent
import os
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
import traceback
import json
import aiofiles

# 存储 Agent 实例的字典（按进程ID区分）
agent_instances = {}
agent_lock = threading.Lock()

# 会话历史记录缓存，按 session_id 存储聊天消息列表
session_histories: Dict[str, List[Dict[str, str]]] = {}
session_history_lock = threading.Lock()

# 历史记录存储目录
HISTORY_DIR = "session_histories"

def ensure_history_dir():
    """确保历史记录目录存在"""
    if not os.path.exists(HISTORY_DIR):
        os.makedirs(HISTORY_DIR)

def get_history_file_path(session_id: str) -> str:
    """获取会话历史文件路径"""
    return os.path.join(HISTORY_DIR, f"{session_id}.json")

async def load_session_history(session_id: str):
    """异步加载会话历史"""
    file_path = get_history_file_path(session_id)
    if os.path.exists(file_path):
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            print(f"加载会话历史失败 {session_id}: {e}")
    return []

async def save_session_history(session_id: str, history: List[Dict[str, str]]):
    """异步保存会话历史"""
    file_path = get_history_file_path(session_id)
    try:
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(history, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"保存会话历史失败 {session_id}: {e}")

def get_or_create_agent():
    """获取或创建当前进程的 Agent 实例"""
    pid = os.getpid()
    with agent_lock:
        if pid not in agent_instances:
            try:
                agent_instances[pid] = create_agent()
                print(f"✅ Agent 在进程 {pid} 中初始化成功")
            except Exception as e:
                print(f"❌ 进程 {pid} 初始化 Agent 失败: {e}")
                raise e
        return agent_instances[pid]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """生命周期管理器"""
    print("🚀 服务启动...")
    ensure_history_dir()
    # 启动时加载所有会话历史
    for filename in os.listdir(HISTORY_DIR):
        if filename.endswith('.json'):
            session_id = filename[:-5]  # 移除.json
            history = await load_session_history(session_id)
            with session_history_lock:
                session_histories[session_id] = history
    print(f"✅ 已加载 {len(session_histories)} 个会话历史")
    yield
    print("🛑 服务关闭...")

app = FastAPI(title="Agent 知识问答 API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建线程池用于处理同步操作
executor = ThreadPoolExecutor(max_workers=5)

# 定义请求数据格式
class ChatRequest(BaseModel):
    question: str
    session_id: str = "default_session"

@app.post("/chat")
async def chat_with_agent(request: ChatRequest):
    """异步处理聊天请求"""
    print(f"\n🔄 收到问题 (Session: {request.session_id}): {request.question}")
    
    try:
        # 获取当前进程的 Agent
        agent_executor = get_or_create_agent()

        # 准备会话历史消息，用于让 Agent 继续上下文对话
        with session_history_lock:
            if request.session_id not in session_histories:
                # 如果内存中没有，尝试从磁盘加载
                history = await load_session_history(request.session_id)
                session_histories[request.session_id] = history
            history = session_histories[request.session_id]

        messages = []
        for item in history:
            messages.append((item["role"], item["content"]))
        messages.append(("user", request.question))

        # 使用线程池来运行同步的 agent.invoke() 操作
        loop = asyncio.get_event_loop()

        def run_agent():
            try:
                result = agent_executor.invoke(
                    {"messages": messages},
                    config={"configurable": {"thread_id": request.session_id}}
                )
                return result
            except Exception as invoke_error:
                print(f"❌ Agent 调用失败: {str(invoke_error)}")
                print(traceback.format_exc())
                raise invoke_error

        result = await loop.run_in_executor(executor, run_agent)

        # 提取 AI 的最终回答
        final_answer = result["messages"][-1].content

        # 将本次消息写入会话历史
        with session_history_lock:
            history.append({"role": "user", "content": request.question})
            history.append({"role": "assistant", "content": final_answer})
            # 异步保存到磁盘
            asyncio.create_task(save_session_history(request.session_id, history))

        print(f"✅ 返回答案: {final_answer[:100]}...")

        return {
            "answer": final_answer,
            "session_id": request.session_id
        }
    except Exception as e:
        error_msg = f"处理请求时出错: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy", 
        "agent_ready": os.getpid() in agent_instances,
        "process_id": os.getpid(),
        "timestamp": asyncio.get_event_loop().time()
    }

@app.get("/history/{session_id}")
async def get_history(session_id: str):
    """获取指定会话的历史消息"""
    return {
        "session_id": session_id,
        "history": session_histories.get(session_id, [])
    }

@app.post("/history/{session_id}/reset")
async def reset_history(session_id: str):
    """清空指定会话的历史记录"""
    with session_history_lock:
        session_histories.pop(session_id, None)
    # 删除对应的文件
    file_path = get_history_file_path(session_id)
    if os.path.exists(file_path):
        os.remove(file_path)
    return {
        "message": f"会话 {session_id} 的历史已重置"
    }

def run_server():
    """运行服务器"""
    import uvicorn
    uvicorn.run(
        "main:app",  # 字符串形式
        host="127.0.0.1",  # 改为本地回环地址
        port=8001,  # 改为8001端口
        log_level="info",
        workers=1,  # 单进程模式，避免 Windows socket 问题
        reload=False,  # 禁用热重载
    )

if __name__ == "__main__":
    print("🚀 启动 Agent 服务...")
    print(f"   PID: {os.getpid()}")
    print("   访问: http://localhost:8001")
    
    run_server()
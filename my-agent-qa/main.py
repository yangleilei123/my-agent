from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agent import create_agent
import os
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
import traceback

# 存储 Agent 实例的字典（按进程ID区分）
agent_instances = {}
agent_lock = threading.Lock()

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
        
        # 使用线程池来运行同步的 agent.invoke() 操作
        loop = asyncio.get_event_loop()
        
        def run_agent():
            try:
                result = agent_executor.invoke(
                    {"messages": [("user", request.question)]},
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

def run_server():
    """运行服务器"""
    import uvicorn
    uvicorn.run(
        "main:app",  # 字符串形式，支持多进程
        host="0.0.0.0", 
        port=8000, 
        log_level="info",
        workers=2,  # 多进程
        reload=False,  # 禁用热重载
    )

if __name__ == "__main__":
    print("🚀 启动 Agent 服务...")
    print(f"   PID: {os.getpid()}")
    print("   访问: http://localhost:8000")
    
    run_server()
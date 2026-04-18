from fastapi import FastAPI, HTTPException, Form # 添加 Form 用于接收文件路径
from pydantic import BaseModel
from agent import create_agent
from rag import ingest_document
import os
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

app = FastAPI(title="Agent 知识问答 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中请指定具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 Agent
try:
    agent_executor = create_agent()
except Exception as e:
    print(f"初始化 Agent 失败: {e}")
    agent_executor = None

# 定义请求数据格式
class ChatRequest(BaseModel):
    question: str
    session_id: str = "default_session"  # 添加会话ID参数

@app.post("/chat")
async def chat_with_agent(request: ChatRequest):
    if agent_executor is None:
        raise HTTPException(status_code=500, detail="Agent 未正确初始化")
    try:
        # LangGraph 的调用方式，传入消息列表
        # 使用 session_id 作为 thread_id
        result = agent_executor.invoke(
            {"messages": [("user", request.question)]},
            config={"configurable": {"thread_id": request.session_id}}  # 关键：传递 thread_id
        )
        
        # 提取 AI 的最终回答 (在消息列表的最后一条)
        final_answer = result["messages"][-1].content
        
        return {
            "answer": final_answer,
            "session_id": request.session_id  # 返回会话ID
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")

@app.post("/upload")
async def upload_doc(file_path: str = Form(...)): # 使用 Form 来接收路径参数
    """
    为了简单起见，这里直接传入本地文件路径进行处理。
    生产环境应改成接收文件上传 (UploadFile)。
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    try:
        ingest_document(file_path)
        return {"message": "文档导入成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入文档时出错: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
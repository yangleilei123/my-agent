# test_agent.py
import asyncio
from langchain_core.messages import SystemMessage, HumanMessage
from agent import create_agent

async def test():
    agent_executor = create_agent()
    
    # 定义一个测试问题
    test_message = "SMART 原则指的是什么？" # 或者换成你文档里的具体问题
    
    # 定义系统提示
    system_prompt = "你是一个超级智能问答助手。你可以使用工具来查阅私有知识库或联网搜索。请根据用户的问题自动选择合适的工具。用中文回答。"
    
    # 构建消息列表，包含系统提示和人类消息
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=test_message)
    ]

    # 重要：每次调用都要传递 thread_id
    thread_id = "test_conversation_001"
    
    # 调用 Agent
    config = {"configurable": {"thread_id": "thread_id"}}
    
    try:
        # 将包含系统消息的消息列表传递给 Agent
        response = await agent_executor.ainvoke({"messages": messages}, config=config)
        print("Agent Response (ainvoke):", response)
    except Exception as e_ainvoke:
        print(f"AInvoke failed: {e_ainvoke}")
        try:
            # 尝试同步调用
            response = agent_executor.invoke({"messages": messages}, config=config)
            print("Agent Response (invoke):", response)
        except Exception as e_invoke:
            print(f"Invoke also failed: {e_invoke}")

if __name__ == "__main__":
    asyncio.run(test())
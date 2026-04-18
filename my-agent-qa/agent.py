from dotenv import load_dotenv
import os
from langchain_core.messages import SystemMessage # 导入 SystemMessage
from langchain_community.chat_models import ChatTongyi
from langchain_core.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun
from langgraph.prebuilt import create_react_agent
from rag import get_retriever
from langgraph.checkpoint.memory import MemorySaver  # 新增：内存检查点

load_dotenv()

def create_agent():
    # a. 初始化大语言模型 (LLM)
    llm = ChatTongyi(
        model="qwen-max",
        temperature=0,
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
    )

    # b. 获取知识库检索器
    # 目的: 从 rag.py 模块中获取一个已经连接到向量数据库（Chroma）的检索器对象。
    # 作用: 这个对象知道如何在你之前通过 ingest.py 导入的文档中查找与用户问题最相关的信息。
    retriever = get_retriever()
    
    # 正确包装 VectorStoreRetriever
    def retrieve_docs(query: str) -> str:
        # retriever.invoke 是同步的，返回 List[Document]
        docs = retriever.invoke(query)
        print(f"找到 {len(docs)} 个相关文档片段")

        # 打印每个文档片段用于调试
        for i, doc in enumerate(docs):
            print(f"文档片段 {i+1}: {doc.page_content[:200]}...")
            print(f"来源: {doc.metadata}")

        # 格式化文档内容
        formatted_docs = "\n\n".join([doc.page_content for doc in docs])
        result = formatted_docs if formatted_docs else "未找到相关信息。"
        print(f"返回给模型的内容: {result[:200]}...")
        return result
    
    # c. 封装知识库工具 (knowledge_tool)
    # 目的: 将 retriever 封装成 LangGraph 能够理解和使用的标准工具（Tool）
    knowledge_tool = Tool(
        name="knowledge_base_tool",
        func=retrieve_docs,
        description="当你被问及关于本地项目、公司规章、特定私有文档的问题时，必须使用此工具。它会返回相关文档片段。优先级最高，必须首先尝试此工具。如果用户询问特定的个人信息、文档内容等，优先使用此工具。"
    )

    # d. 创建网络搜索工具 (search_tool)
    # 目的: 创建另一个工具，用于进行实时网络搜索。
    # 作用: 当用户问题涉及的知识库外的最新信息时，Agent 可以使用这个工具。
    # DuckDuckGoSearchRun: LangChain 提供的一个内置工具，封装了对 DuckDuckGo 搜索引擎的 API 调用。
    search_tool = DuckDuckGoSearchRun(
        name="web_search",
        description="当知识库中找不到答案，或者用户询问最新新闻、天气等实时信息时，使用此工具搜网。"
    )

    # e. 组合工具列表
    # 目的: 将所有可用的工具放入一个列表中，方便传递给 Agent 创建函数。
    tools = [knowledge_tool, search_tool]

    # f. (隐式) 定义 Agent 角色和规则
    # 目的: 定义 Agent 的角色和行为准则。虽然没有直接传递给 create_react_agent（因为我们移除了 state_modifier），但我们在调用 Agent 时（如 test_agent.py 或 main.py）会将这条信息作为 SystemMessage 传入。这是告诉 LLM 如何思考和行动的关键指令。
    # Agent 的人设和系统提示词
    system_prompt = "你是一个超级智能问答助手。你可以使用工具来查阅私有知识库或联网搜索。请根据用户的问题自动选择合适的工具。用中文回答。"
    
    # 创建包含系统提示的初始消息列表
    initial_messages = [SystemMessage(content=system_prompt)]

    # f. Agent 的人设和系统提示词
    system_prompt = """你是一个超级智能问答助手。你的行为准则如下：

1. 优先原则：对于任何问题，你必须首先使用 knowledge_base_tool 查阅私有知识库
2. 顺序原则：只有在知识库中没有找到相关信息时，才使用 web_search 进行网络搜索
3. 诚实原则：如果两个工具都找不到答案，诚实地告诉用户没有找到相关信息
4. 语言原则：始终用中文回答

记住：用户可能询问私人信息、特定文档内容、公司内部资料等，这些都应该首先在知识库中查找。"""

    # f. 创建内存检查点
    memory = MemorySaver()

    # g. 创建 Agent 执行器 
    # 目的: 这是关键一步，使用 LangGraph 提供的 create_react_agent 函数，将 LLM 和 Tools 组合起来，创建一个完整的、可执行的 Agent。
    # create_react_agent:
    #     它内部实现了一个经典的 ReAct (Reasoning + Acting) 循环。
    #     Reasoning: Agent (LLM) 收到用户输入后，分析问题，思考下一步应该做什么（是回答还是使用工具）。
    #     Acting: 如果决定使用工具，Agent 会选择一个工具，并准备相应的参数，然后执行该工具。
    #     Observation: 工具执行后返回结果，Agent (LLM) 会“观察”到这个结果。
    #     Repeat: Agent 再次进行 Reasoning，基于之前的对话历史和工具结果，决定是继续使用工具还是给出最终答案。
    # 使用 messages 参数传递系统提示
    # 注意：根据最新的 langgraph 版本，可能需要通过 config 或者其他方式设置
    # 如果 create_react_agent 不直接支持 messages，我们稍后再调整
    agent_executor = create_react_agent(
        model=llm, 
        tools=tools,
        # messages=initial_messages # 这个参数可能也不对，让我们先移除它
        checkpointer=memory  # 启用内存
    )
    
    # 如果需要，我们可以创建一个包装函数来在每次调用时注入系统消息
    def wrapped_invoke(inputs, config=None):
        # inputs 应该是 {"messages": [...]}
        # 在消息列表开头插入系统消息
        if "messages" in inputs:
            messages = initial_messages + inputs["messages"]
            inputs["messages"] = messages
        return agent_executor.invoke(inputs, config)
        
    # h. 返回 Agent
    # 目的: 将创建好的 Agent 执行器对象返回给调用者（如 main.py 或 test_agent.py），以便后续可以向它发送问题并接收回答。
    # 返回包装过的执行器，或者直接返回原始执行器看默认行为如何
    # return wrapped_invoke 
    return agent_executor # 先尝试返回原始执行器，看是否能从调用处传入系统消息
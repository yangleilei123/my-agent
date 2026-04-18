import os
import warnings
from dotenv import load_dotenv

# 抑制 LangChain 弃用警告
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain_core._api.deprecation")

# 加载环境变量
load_dotenv()

# 如果你想彻底解决 Chroma 弃用问题，取消下面这行注释，并注释掉 from langchain_community.vectorstores import Chroma
# pip install -U langchain-chroma
# from langchain_chroma import Chroma 
from langchain_community.vectorstores import Chroma # 当前使用的版本
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import DashScopeEmbeddings

# 初始化向量模型 (使用千问的Embedding)
embeddings = DashScopeEmbeddings(
    model="text-embedding-v3",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
)
# 定义向量数据库存储路径
CHROMA_DIR = "./chroma_db"

def ingest_document(file_path: str):
    """将文档导入向量数据库"""
    print(f"正在加载文档: {file_path}")
    
    if file_path.lower().endswith('.pdf'):
        loader = PyPDFLoader(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {file_path}")
        
    docs = loader.load()
    
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    print(f"文档已切分为 {len(chunks)} 块")

    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    vectorstore.add_documents(chunks)
    print("文档向量化并存入数据库成功！")

def get_retriever():
    """获取知识库检索器"""
    if not os.path.exists(CHROMA_DIR):
        print(f"警告: 向量数据库 {CHROMA_DIR} 不存在，请先导入文档。")
        raise RuntimeError("无法加载向量数据库，请检查是否已导入文档。")
        
    try:
        db = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    except ValueError as e:
        print(f"加载向量数据库时出错: {e}")
        raise RuntimeError("无法加载向量数据库，请检查是否已导入文档。")
        
    # 返回 VectorStoreRetriever 对象
    # 注意：VectorStoreRetriever 没有 get_relevant_documents 方法，但它有 invoke 方法
    # retriever.invoke(query) -> List[Document]
    # retriever.aget_relevant_documents(query) -> List[Document] (async)
    # retriever.get_relevant_documents(query) -> 这个方法不存在
    return db.as_retriever(search_kwargs={"k": 3})
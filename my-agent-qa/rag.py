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
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    CSVLoader,
    Docx2txtLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredExcelLoader,
    UnstructuredHTMLLoader,
    JSONLoader,
    UnstructuredMarkdownLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import DashScopeEmbeddings

# 初始化向量模型 (使用千问的Embedding)
embeddings = DashScopeEmbeddings(
    model="text-embedding-v3",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
)
# 定义向量数据库存储路径
CHROMA_DIR = "./chroma_db"

def get_loader_for_file(file_path: str):
    """根据文件扩展名返回相应的加载器"""
    # 修正：使用 os.path.splitext 正确提取扩展名
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    loaders = {
        '.pdf': PyPDFLoader,
        '.txt': TextLoader,
        '.csv': CSVLoader,
        '.docx': Docx2txtLoader,
        '.doc': UnstructuredWordDocumentLoader,
        '.xlsx': UnstructuredExcelLoader,
        '.xls': UnstructuredExcelLoader,
        '.html': UnstructuredHTMLLoader,
        '.htm': UnstructuredHTMLLoader,
        '.json': JSONLoader,
        '.md': UnstructuredMarkdownLoader,
        '.markdown': UnstructuredMarkdownLoader,
    }
    
    if ext not in loaders:
        raise ValueError(f"不支持的文件格式: {ext}. 支持的格式: {list(loaders.keys())}")
    
    loader_class = loaders[ext]
    
    # 特殊处理一些需要额外参数的加载器
    if ext in ['.txt', '.html', '.htm', '.md', '.markdown']:
        # TextLoader 和 HTML 加载器需要 encoding 参数
        return loader_class(file_path, encoding='utf-8')
    elif ext in ['.json']:
        # JSONLoader 需要 jq_schema 参数
        return loader_class(file_path, jq_schema=".", text_content=False)
    elif ext in ['.csv']:
        # CSVLoader 可能需要指定列
        return loader_class(file_path)
    else:
        return loader_class(file_path)

def ingest_document(file_path: str):
    """将文档导入向量数据库"""
    print(f"正在加载文档: {file_path}")

    # 获取适当的加载器
    loader = get_loader_for_file(file_path)
    # 加载文档
    docs = loader.load()

    # 打印文档内容预览
    print(f"文档内容预览（前200字符）: {docs[0].page_content[:200]}...")

    # 文档分割
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,  # 进一步增大块大小
        chunk_overlap=150,  # 增加重叠
        separators=[
            "\n\n", "\n", "。", "！", "？", "；", ":", 
            ".", "!", "?", ";", " ", ""
        ]
    )
    chunks = splitter.split_documents(docs)
    print(f"文档已切分为 {len(chunks)} 块")

    # 打印每个块的预览
    for i, chunk in enumerate(chunks):
        preview = chunk.page_content[:100] if len(chunk.page_content) > 100 else chunk.page_content
        has_target = "杨雷雷" in chunk.page_content
        status = "✅" if has_target else "   "
        print(f"  {status} 块 {i+1} 预览: {preview}...")

    # 创建或连接向量数据库
    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    vectorstore.add_documents(chunks)
    print("文档向量化并存入数据库成功！")

# 辅助函数：批量导入多个文件
def batch_ingest(file_paths: list):
    """批量导入多个文件"""
    for file_path in file_paths:
        try:
            print(f"开始处理: {file_path}")
            ingest_document(file_path)
            print(f"✓ {file_path} 处理完成")
        except Exception as e:
            print(f"✗ {file_path} 处理失败: {str(e)}")

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
    # 使用相似度搜索，设置更高的相似度阈值
    return db.as_retriever(
        search_kwargs={
            "k": 10,  # 增加返回结果数量
            "score_threshold": 0.1  # 设置相似度阈值
        },
        search_type="similarity_score_threshold"  # 使用相似度分数阈值搜索
    )
        
# 辅助函数：检查支持的文件格式
def supported_formats():
    """返回支持的文件格式列表"""
    return [
        ".pdf", ".txt", ".csv", ".docx", ".doc", 
        ".xlsx", ".xls", ".html", ".htm", 
        ".json", ".md", ".markdown"
    ]

if __name__ == "__main__":
    # 测试支持的格式
    print("支持的文件格式:", supported_formats())
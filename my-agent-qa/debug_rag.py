import os
from rag import get_retriever

def debug_retrieval():
    """调试检索功能"""
    print("🔍 开始调试 RAG 检索功能...")
    
    try:
        # 获取检索器
        retriever = get_retriever()
        print("✅ 成功加载检索器")
        
        # 测试查询
        queries = ["杨雷雷是谁", "杨雷雷简介", "杨雷雷"]
        
        for query in queries:
            print(f"\n--- 测试查询: '{query}' ---")
            try:
                # 执行检索 - 使用正确的API
                results = retriever.invoke(query)
                
                print(f"找到 {len(results)} 个相关文档片段:")
                
                for i, doc in enumerate(results, 1):
                    print(f"\n片段 {i}:")
                    print(f"内容: {doc.page_content[:200]}...")  # 显示前200字符
                    print(f"来源: {doc.metadata}")
                    
                    # 检查是否包含目标关键词
                    if "杨雷雷" in doc.page_content:
                        print("✅ 包含'杨雷雷'关键词")
                    else:
                        print("❌ 不包含'杨雷雷'关键词")
                        
            except Exception as e:
                print(f"❌ 检索失败: {str(e)}")
                
    except Exception as e:
        print(f"❌ 加载检索器失败: {str(e)}")
        print("请确保已正确导入文档")

def check_vector_db():
    """检查向量数据库状态"""
    from rag import CHROMA_DIR
    
    if os.path.exists(CHROMA_DIR):
        print(f"✅ 向量数据库存在: {CHROMA_DIR}")
        
        # 统计数据库中的文档数量
        import chromadb
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings import DashScopeEmbeddings
        
        # 重新加载数据库来检查内容
        embeddings = DashScopeEmbeddings(
            model="text-embedding-v3",
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
        )
        
        try:
            db = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
            collection = db._collection
            count = collection.count()
            print(f"数据库中共有 {count} 个文档片段")
            
            # 获取所有文档片段进行检查
            all_docs = collection.get(limit=count)
            print(f"实际存储的文档片段数量: {len(all_docs['documents'])}")
            
            for i, doc_content in enumerate(all_docs['documents']):
                preview = doc_content[:100] if len(doc_content) > 100 else doc_content
                has_target = "杨雷雷" in doc_content
                status = "✅" if has_target else "❌"
                print(f"  {status} 片段 {i+1}: {preview}...")
                
        except Exception as e:
            print(f"❌ 读取数据库内容失败: {str(e)}")
    else:
        print(f"❌ 向量数据库不存在: {CHROMA_DIR}")

if __name__ == "__main__":
    print("=== RAG 调试工具 ===\n")
    
    check_vector_db()
    print()
    debug_retrieval()
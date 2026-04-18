import os
import sys
from rag import batch_ingest, supported_formats

def process_docs_folder(docs_path="./docs"):
    """处理 docs 目录下的所有支持格式的文档"""
    if not os.path.exists(docs_path):
        print(f"目录不存在: {docs_path}")
        return False
    
    # 获取支持的文件格式
    supported_exts = set(supported_formats())
    
    # 获取目录下所有支持格式的文件
    files_to_process = []
    for filename in os.listdir(docs_path):
        file_path = os.path.join(docs_path, filename)
        if os.path.isfile(file_path):
            ext = os.path.splitext(filename)[1].lower()
            if ext in supported_exts:
                files_to_process.append(file_path)
    
    if not files_to_process:
        print(f"在 {docs_path} 目录下没有找到支持的文档格式: {supported_exts}")
        print(f"支持的格式: {', '.join(supported_formats())}")
        return False
    
    print(f"找到 {len(files_to_process)} 个文档:")
    for file_path in files_to_process:
        print(f"  - {os.path.basename(file_path)}")
    
    print("\n开始处理文档...")
    try:
        batch_ingest(files_to_process)
        print("✅ 文档处理完成！")
        return True
    except Exception as e:
        print(f"❌ 文档处理失败: {str(e)}")
        return False

def clear_vector_db():
    """清空向量数据库"""
    import shutil
    from rag import CHROMA_DIR
    
    if os.path.exists(CHROMA_DIR):
        try:
            shutil.rmtree(CHROMA_DIR)
            print(f"✅ 向量数据库已清空: {CHROMA_DIR}")
            return True
        except Exception as e:
            print(f"❌ 清空向量数据库失败: {str(e)}")
            return False
    else:
        print(f"⚠️ 向量数据库不存在: {CHROMA_DIR}")
        return True
    
def verify_documents(docs_path="./docs"):
    """验证文档内容"""
    import re
    print(f"\n🔍 验证文档内容...")
    
    # 获取支持的文件格式
    supported_exts = set(supported_formats())
    
    for filename in os.listdir(docs_path):
        file_path = os.path.join(docs_path, filename)
        if os.path.isfile(file_path):
            ext = os.path.splitext(filename)[1].lower()
            if ext in supported_exts:
                print(f"\n📄 检查文件: {filename}")
                
                # 尝试读取文件内容（简单验证）
                if ext in ['.txt', '.md', '.markdown']:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            print(f"   内容长度: {len(content)} 字符")
                            
                            # 检查是否包含关键信息
                            if '杨雷雷' in content:
                                print("   ✅ 包含'杨雷雷'关键词")
                            else:
                                print("   ⚠️ 未找到'杨雷雷'关键词")
                    except:
                        print(f"   ❌ 无法读取文件内容")
                        
                elif ext == '.pdf':
                    # PDF文件需要特殊处理
                    try:
                        from langchain_community.document_loaders import PyPDFLoader
                        loader = PyPDFLoader(file_path)
                        pages = loader.load()
                        full_text = ""
                        for page in pages:
                            full_text += page.page_content
                        
                        print(f"   内容长度: {len(full_text)} 字符")
                        if '杨雷雷' in full_text:
                            print("   ✅ 包含'杨雷雷'关键词")
                        else:
                            print("   ⚠️ 未找到'杨雷雷'关键词")
                    except:
                        print(f"   ❌ 无法读取PDF文件内容")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='文档向量化工具')
    parser.add_argument('--docs-path', type=str, default='./docs', help='文档目录路径')
    parser.add_argument('--clear', action='store_true', help='清空现有向量数据库')
    parser.add_argument('--list-formats', action='store_true', help='列出支持的文件格式')
    parser.add_argument('--verify', action='store_true', help='验证文档内容')
    
    args = parser.parse_args()
    
    if args.list_formats:
        print("支持的文件格式:")
        for fmt in supported_formats():
            print(f"  - {fmt}")
        return
    
    if args.clear:
        print("正在清空向量数据库...")
        if clear_vector_db():
            print("请重新运行脚本来处理新文档")
            return
    
    if args.verify:
        verify_documents(args.docs_path)
        return
    
    print(f"开始处理文档目录: {args.docs_path}")
    success = process_docs_folder(args.docs_path)
    
    if success:
        print(f"\n🎉 文档处理完成！")
        print(f"向量数据库已保存到: ./chroma_db")
        print(f"现在可以启动 API 服务进行问答了")
    else:
        print(f"\n❌ 文档处理失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main()
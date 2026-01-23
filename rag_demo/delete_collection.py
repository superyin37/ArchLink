"""
删除 Chroma 中的 collection（交互式）
支持删除案例库、规范库或全部
"""
import os
import shutil
from langchain_chroma import Chroma
from embeddings import DoubaoVisionEmbeddings
from dotenv import load_dotenv

load_dotenv()

def delete_collection(collection_name: str, hash_file: str, persist_dir: str = "./chroma_db"):
    """
    删除指定的 collection
    
    Args:
        collection_name: collection 名称
        hash_file: 对应的状态文件
        persist_dir: 向量库目录
    """
    print(f"\n准备删除 collection: {collection_name}")
    print(f"向量库目录: {persist_dir}")
    
    try:
        # 初始化向量库
        doubao_emb = DoubaoVisionEmbeddings()
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=doubao_emb,
            persist_directory=persist_dir
        )
        
        # 删除 collection
        vectorstore.delete_collection()
        print(f"✓ 成功删除 collection: {collection_name}")
        
    except Exception as e:
        print(f"✗ 删除 collection 失败: {e}")
        return False
    
    # 删除处理状态文件
    if os.path.exists(hash_file):
        os.remove(hash_file)
        print(f"✓ 删除状态文件: {hash_file}")
    else:
        print(f"⚠ 状态文件不存在: {hash_file}")
    
    return True

def delete_all_collections(persist_dir: str = "./chroma_db"):
    """删除所有 collections 和向量库"""
    print(f"\n准备删除整个向量库目录: {persist_dir}")
    
    if os.path.exists(persist_dir):
        try:
            shutil.rmtree(persist_dir)
            print(f"✓ 成功删除向量库目录: {persist_dir}")
        except Exception as e:
            print(f"✗ 删除向量库目录失败: {e}")
            return False
    else:
        print(f"⚠ 向量库目录不存在: {persist_dir}")
    
    # 删除所有状态文件
    hash_files = [
        "processed_chunk_hashes_anliku.json",
        "processed_chunk_hashes_guifan.json",
        "processed_chunk_hashes.json"
    ]
    
    for hash_file in hash_files:
        if os.path.exists(hash_file):
            os.remove(hash_file)
            print(f"✓ 删除状态文件: {hash_file}")
    
    return True

def main():
    """主函数：交互式选择删除选项"""
    print("=" * 60)
    print("Chroma Collection 删除工具")
    print("=" * 60)
    print("\n请选择要删除的 collection:")
    print("1. 案例库 (anliku)")
    print("2. 规范库 (guifan)")
    print("3. 全部删除（包括向量库目录）")
    print("0. 取消")
    
    try:
        choice = input("\n请输入选项 (0-3): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\n操作已取消")
        return
    
    if choice == "0":
        print("\n操作已取消")
        return
    
    elif choice == "1":
        # 删除案例库
        success = delete_collection(
            collection_name="anliku",
            hash_file="processed_chunk_hashes_anliku.json"
        )
        if success:
            print("\n✓ 案例库清理完成！")
            print("可以运行 uv run load_splits_anliku.py 重新加载数据")
    
    elif choice == "2":
        # 删除规范库
        success = delete_collection(
            collection_name="guifan",
            hash_file="processed_chunk_hashes_guifan.json"
        )
        if success:
            print("\n✓ 规范库清理完成！")
            print("可以运行 uv run load_splits_guifan.py 重新加载数据")
    
    elif choice == "3":
        # 确认删除全部
        print("\n⚠️  警告：这将删除所有 collections 和向量库目录！")
        confirm = input("确认删除全部？(yes/no): ").strip().lower()
        
        if confirm in ["yes", "y"]:
            success = delete_all_collections()
            if success:
                print("\n✓ 全部清理完成！")
                print("可以运行以下命令重新加载数据：")
                print("  - uv run load_splits_anliku.py  (案例库)")
                print("  - uv run load_splits_guifan.py  (规范库)")
        else:
            print("\n操作已取消")
    
    else:
        print("\n✗ 无效的选项")

if __name__ == "__main__":
    main()


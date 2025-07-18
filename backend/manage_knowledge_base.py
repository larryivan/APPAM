#!/usr/bin/env python3
"""
知识库管理脚本
用于初始化、刷新和管理知识库
"""

import os
import sys
import argparse
from pathlib import Path

# 添加app目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.knowledge_base import KnowledgeBaseService

def main():
    parser = argparse.ArgumentParser(description='知识库管理工具')
    parser.add_argument('--action', choices=['init', 'refresh', 'stats', 'search'], 
                       default='init', help='执行的操作')
    parser.add_argument('--query', type=str, help='搜索查询（用于search操作）')
    parser.add_argument('--top-k', type=int, default=5, help='返回的搜索结果数量')
    parser.add_argument('--force', action='store_true', help='强制重建知识库')
    
    args = parser.parse_args()
    
    # 初始化知识库服务
    knowledge_service = KnowledgeBaseService()
    
    if args.action == 'init':
        print("正在初始化知识库...")
        try:
            knowledge_service.build_knowledge_base(force_rebuild=args.force)
            print("知识库初始化完成！")
        except Exception as e:
            print(f"初始化知识库失败: {e}")
            sys.exit(1)
    
    elif args.action == 'refresh':
        print("正在刷新知识库...")
        try:
            knowledge_service.refresh_knowledge_base()
            print("知识库刷新完成！")
        except Exception as e:
            print(f"刷新知识库失败: {e}")
            sys.exit(1)
    
    elif args.action == 'stats':
        print("获取知识库统计信息...")
        try:
            stats = knowledge_service.get_knowledge_stats()
            print(f"\n知识库统计信息:")
            print(f"  总文档块数: {stats['total_chunks']}")
            print(f"  数据库路径: {stats['database_path']}")
            print(f"  文档来源:")
            for source, count in stats['document_sources'].items():
                print(f"    {source}: {count} 个块")
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            sys.exit(1)
    
    elif args.action == 'search':
        if not args.query:
            print("搜索操作需要提供查询内容 (--query)")
            sys.exit(1)
        
        print(f"搜索知识库: '{args.query}'")
        try:
            results = knowledge_service.search_knowledge(args.query, args.top_k)
            print(f"\n找到 {len(results)} 个相关结果:")
            
            for i, result in enumerate(results, 1):
                print(f"\n{i}. 来源: {result['metadata'].get('filename', '未知')}")
                print(f"   相似度: {result['similarity']:.3f}")
                print(f"   内容预览: {result['content'][:200]}...")
                print("-" * 50)
        except Exception as e:
            print(f"搜索失败: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main() 
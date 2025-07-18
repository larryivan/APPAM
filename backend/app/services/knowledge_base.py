
import os
import glob
from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import chromadb
from sentence_transformers import SentenceTransformer
import json
import logging
from datetime import datetime

# 使用最新的import方式
try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
except ImportError:
    from langchain.embeddings import HuggingFaceEmbeddings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KnowledgeBaseService:
    def __init__(self, knowledge_dir: str = "knowledge"):
        self.knowledge_dir = knowledge_dir
        self.chroma_db_path = os.path.join(knowledge_dir, "chroma_db")
        # 使用更稳定的中文嵌入模型
        try:
            self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"无法加载嵌入模型: {e}")
            # 使用备用模型
            self.embeddings_model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200,
            length_function=len
        )
        self.client = None
        self.collection = None
        self._initialize_database()
    
    def _initialize_database(self):
        """初始化ChromaDB数据库"""
        try:
            # 创建目录
            os.makedirs(self.chroma_db_path, exist_ok=True)
            
            # 初始化ChromaDB客户端，禁用遥测功能以避免posthog兼容性问题
            self.client = chromadb.PersistentClient(
                path=self.chroma_db_path,
                settings=chromadb.Settings(anonymized_telemetry=False)
            )
            
            # 获取或创建集合
            try:
                self.collection = self.client.get_collection(name="knowledge_base")
                logger.info("加载现有的知识库集合")
            except:
                self.collection = self.client.create_collection(name="knowledge_base")
                logger.info("创建新的知识库集合")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def load_markdown_documents(self) -> List[Document]:
        """加载knowledge目录下的所有markdown文档"""
        documents = []
        
        # 查找所有markdown文件
        markdown_patterns = [
            os.path.join(self.knowledge_dir, "*.md"),
            os.path.join(self.knowledge_dir, "**/*.md"),
            os.path.join(self.knowledge_dir, "**/**/*.md")
        ]
        
        markdown_files = []
        for pattern in markdown_patterns:
            markdown_files.extend(glob.glob(pattern, recursive=True))
        
        # 去重
        markdown_files = list(set(markdown_files))
        
        logger.info(f"发现 {len(markdown_files)} 个markdown文件")
        
        for file_path in markdown_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 创建文档对象
                doc = Document(
                    page_content=content,
                    metadata={
                        'source': file_path,
                        'filename': os.path.basename(file_path),
                        'file_type': 'markdown'
                    }
                )
                documents.append(doc)
                logger.info(f"加载文档: {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to load document {file_path}: {e}")
                continue
        
        return documents
    
    def build_knowledge_base(self, force_rebuild: bool = False):
        """构建知识库"""
        try:
            # 检查是否需要重建
            if not force_rebuild and self.collection.count() > 0:
                logger.info("知识库已存在，跳过构建")
                return
            
            # 清空现有数据（如果强制重建）
            if force_rebuild:
                try:
                    self.client.delete_collection(name="knowledge_base")
                    self.collection = self.client.create_collection(name="knowledge_base")
                    logger.info("清空现有知识库数据")
                except:
                    pass
            
            # 加载markdown文档
            documents = self.load_markdown_documents()
            
            if not documents:
                logger.warning("没有找到markdown文档")
                return
            
            # 分割文档
            texts = self.text_splitter.split_documents(documents)
            logger.info(f"文档分割成 {len(texts)} 个块")
            
            # 准备数据
            ids = []
            embeddings = []
            metadatas = []
            documents_content = []
            
            for i, text in enumerate(texts):
                # 生成嵌入
                embedding = self.embeddings_model.encode(text.page_content).tolist()
                
                ids.append(f"doc_{i}")
                embeddings.append(embedding)
                metadatas.append(text.metadata)
                documents_content.append(text.page_content)
            
            # 批量插入ChromaDB
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_content
            )
            
            logger.info(f"Successfully built knowledge base with {len(texts)} document chunks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to build knowledge base: {e}")
            return False
    
    def search_knowledge(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索知识库"""
        try:
            # 生成查询嵌入
            query_embedding = self.embeddings_model.encode(query).tolist()
            
            # 搜索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            # 检查结果是否有效
            if not results:
                return []
            
            documents = results.get('documents', [])
            metadatas = results.get('metadatas', [])
            distances = results.get('distances', [])
            
            # 确保所有数据都存在且不为空
            if not documents or not documents[0] or not metadatas or not metadatas[0] or not distances or not distances[0]:
                return []
            
            # 格式化结果
            formatted_results = []
            for i in range(len(documents[0])):
                # 修复相似度计算 - ChromaDB距离越小越相似
                distance = distances[0][i]
                # 使用简单的相似度计算，距离越小相似度越高
                similarity = max(0.0, 1.0 / (1.0 + distance)) if distance >= 0 else 1.0
                
                formatted_results.append({
                    'content': documents[0][i],
                    'metadata': metadatas[0][i],
                    'similarity': similarity
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search knowledge base: {e}")
            return []

    def get_knowledge_context(self, query: str, top_k: int = 5) -> str:
        """Get context from knowledge base for a query"""
        try:
            results = self.search_knowledge(query, top_k)
            if results:
                context = "\n\n".join([doc['content'] for doc in results])
                return context
            return ""
        except Exception as e:
            logger.error(f"Failed to get knowledge base context: {e}")
            return ""

    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        try:
            # This is a simple implementation - you might want to add more detailed stats
            collection = self.collection
            count = collection.count()
            return {
                "total_documents": count,
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get knowledge base statistics: {e}")
            return {"error": str(e)}
    
    def refresh_knowledge_base(self):
        """刷新知识库"""
        self.build_knowledge_base(force_rebuild=True)

# 全局实例
knowledge_base = KnowledgeBaseService()

# 旧版本兼容函数
def create_knowledge_base(documents):
    """向后兼容的函数"""
    logger.warning("使用了已废弃的create_knowledge_base函数，请使用KnowledgeBaseService")
    return knowledge_base

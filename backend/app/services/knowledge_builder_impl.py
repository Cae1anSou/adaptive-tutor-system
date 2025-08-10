# backend/app/services/knowledge_builder_impl.py
import os
import json
from typing import List, Iterator
from openai import OpenAI
from annoy import AnnoyIndex
from app.core.document import Document
from app.core.rag_knowledge_builder import KnowledgeBaseBuilder
from app.core.config import settings
from app.services.markdown_loader import MarkdownLoader

class KnowledgeBaseBuilderImpl(KnowledgeBaseBuilder):
    """知识库构建器实现"""
    
    def __init__(self):
        self.documents: List[Document] = []
        self.embeddings: List[List[float]] = []
        self.index: AnnoyIndex = None
        self.chunk_size = 500  # 每个文本块的最大字符数
        self.chunk_overlap = 50  # 文本块之间的重叠字符数
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            base_url=settings.TUTOR_EMBEDDING_API_BASE,
            api_key=settings.TUTOR_EMBEDDING_API_KEY,
        )
        self.embedding_model = settings.TUTOR_EMBEDDING_MODEL
        self.embedding_dimension = 2560  # Qwen3-Embedding-4B-GGUF的维度
        
    def build_from_documents(self, documents: List[Document]) -> bool:
        """从文档列表构建知识库"""
        self.documents = documents
        text_chunks = self._chunk_documents(documents)
        self.embeddings = self._get_embeddings_batch(text_chunks)
        self.index = self._build_annoy_index(self.embeddings)
        return True
    
    def build_from_directory(self, directory_path: str, recursive: bool = True) -> bool:
        """从目录构建知识库"""
        loader = MarkdownLoader()
        print("开始从目录加载文档...")
        documents = list(loader.load_from_directory(directory_path, recursive))
        print(f"文档加载完成，共加载 {len(documents)} 个有效文档。")
        return self.build_from_documents(documents)
    
    def save(self, vector_store_path: str) -> bool:
        """保存知识库到指定路径"""
        if not self.index or not self.documents:
            raise ValueError("Knowledge base not built yet")
        
        # 确保目录存在
        os.makedirs(vector_store_path, exist_ok=True)
        
        # 保存Annoy索引
        ann_path = os.path.join(vector_store_path, settings.KB_ANN_FILENAME)
        self.index.save(ann_path)
        
        # 保存文档块
        chunks_path = os.path.join(vector_store_path, settings.KB_CHUNKS_FILENAME)
        text_chunks = self._chunk_documents(self.documents)
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(text_chunks, f, ensure_ascii=False, indent=2)
        
        return True
    
    def load(self, vector_store_path: str) -> bool:
        """从指定路径加载知识库"""
        # 实现加载逻辑（如果需要）
        # 当前版本主要关注构建和保存
        raise NotImplementedError("Loading from existing index not implemented yet")
    
    def _chunk_documents(self, documents: List[Document]) -> List[str]:
        """将文档切分为文本块"""
        print("开始切分文档为文本块...")
        chunks = []
        for i, doc in enumerate(documents):
            if (i + 1) % 100 == 0:
                print(f"  正在处理第 {i + 1}/{len(documents)} 个文档...")
            # 对于每个文档，将其内容切分为多个重叠的文本块
            content = doc.content
            if len(content) <= self.chunk_size:
                chunks.append(content)
            else:
                # 创建重叠的文本块
                start = 0
                while start < len(content):
                    end = min(start + self.chunk_size, len(content))
                    chunk = content[start:end]
                    chunks.append(chunk)
                    start += self.chunk_size - self.chunk_overlap
                    # 如果剩余内容不足一个chunk，则停止
                    if end == len(content):
                        break
        print(f"文档切分完成，共生成 {len(chunks)} 个文本块。")
        return chunks
    
    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本的embeddings"""
        embeddings = []
        batch_size = 10  # 与原脚本保持一致
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batch_embeddings = []
            
            for text in batch_texts:
                try:
                    response = self.client.embeddings.create(
                        model=self.embedding_model,
                        input=text,
                        encoding_format="float"
                    )
                    batch_embeddings.append(response.data[0].embedding)
                except Exception as e:
                    print(f"API调用错误: '{text[:50]}...': {e}")
                    batch_embeddings.append([0.0] * self.embedding_dimension)
            
            embeddings.extend(batch_embeddings)
            print(f"Processed batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
        
        # 验证所有embedding维度一致
        for i, emb in enumerate(embeddings):
            if len(emb) != self.embedding_dimension:
                print(f"Warning: Embedding {i} has dimension {len(emb)}, padding/truncating to {self.embedding_dimension}")
                if len(emb) < self.embedding_dimension:
                    emb.extend([0.0] * (self.embedding_dimension - len(emb)))
                else:
                    embeddings[i] = emb[:self.embedding_dimension]
        
        return embeddings
    
    def _build_annoy_index(self, embeddings: List[List[float]]) -> AnnoyIndex:
        """构建Annoy索引"""
        if not embeddings:
            raise ValueError("No embeddings to build index")
        
        dimension = len(embeddings[0])
        annoy_index = AnnoyIndex(dimension, 'angular')  # 'angular' is recommended for cosine-based embeddings
        
        for i, vector in enumerate(embeddings):
            annoy_index.add_item(i, vector)
        
        annoy_index.build(10)  # 10棵树，树越多精度越高，但索引越大
        return annoy_index
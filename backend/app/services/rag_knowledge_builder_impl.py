# backend/app/services/rag_knowledge_builder_impl.py
import os
import json
from typing import List, Optional
from openai import OpenAI
from annoy import AnnoyIndex
from app.core.document import Document
from app.core.rag_knowledge_builder import KnowledgeBaseBuilder
from app.core.config import settings
from app.services.markdown_loader import MarkdownLoader
from app.services.build_state import BuildState

class KnowledgeBaseBuilderImpl(KnowledgeBaseBuilder):
    """知识库构建器实现"""
    
    def __init__(self, state_file_path: Optional[str] = None):
        self.documents: List[Document] = []
        self.embeddings: List[List[float]] = []
        self.index: Optional[AnnoyIndex] = None
        self.chunk_size = 500  # 每个文本块的最大字符数
        self.chunk_overlap = 50  # 文本块之间的重叠字符数
        self.state: Optional[BuildState] = None
        
        # 如果提供了状态文件路径，初始化BuildState
        if state_file_path:
            self.state = BuildState(state_file_path)
        
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
        
        # 如果有状态管理器，设置路径信息
        if self.state:
            # 设置embeddings和索引的保存路径
            # 使用backend/app/data/checkpoints目录
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            checkpoints_dir = os.path.join(project_root, "app", "data", "checkpoints")
            embeddings_path = os.path.join(checkpoints_dir, "embeddings.json")
            index_path = os.path.join(checkpoints_dir, "index.ann")
            self.state.set_paths(embeddings_path, index_path)
            
            # 确保checkpoints目录存在
            os.makedirs(checkpoints_dir, exist_ok=True)
        
        # 构建知识库
        result = self.build_from_documents(documents)
        
        # 如果有状态管理器且构建成功，标记构建完成
        if self.state and result:
            self.state.mark_build_completed()
        
        return result
    
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
        batch_size = 100  # 与原脚本保持一致
        
        # 如果有可恢复的检查点，从检查点恢复进度
        start_index = 0
        if self.state and self.state.is_resumable():
            progress = self.state.get_progress()
            # 使用已处理的文本块数作为起始索引，而不是批次索引
            start_index = progress["processed_chunks"]
            embeddings = self._load_partial_embeddings()
            print(f"从检查点恢复进度: 已处理 {progress['processed_chunks']}/{progress['total_chunks']} 个文本块")
        
        total_batches = (len(texts)-1)//batch_size + 1
        print(f"开始处理 {len(texts)} 个文本块，共 {total_batches} 个批次...")
        
        for i in range(start_index, len(texts), batch_size):
            # 中断信号已经在KeyboardInterrupt异常处理中处理
            # 这里不再需要额外的检查
            
            batch_index = i//batch_size + 1
            batch_texts = texts[i:i+batch_size]
            batch_embeddings = []
            
            print(f"正在处理批次 {batch_index}/{total_batches} (包含 {len(batch_texts)} 个文本块)...")
            
            try:
                # 使用真正的批量API调用，一次性处理整个批次
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=batch_texts,
                    encoding_format="float"
                )
                batch_embeddings = [item.embedding for item in response.data]
                
            except KeyboardInterrupt:
                print("\n捕获到中断信号，正在保存当前进度...")
                # 重新抛出异常，以便上层脚本可以捕获并优雅退出
                raise
            except Exception as e:
                print(f"API调用错误: {e}")
                # 如果批量调用失败，回退到单个处理
                print("回退到单个文本块处理...")
                for text in batch_texts:
                    try:
                        response = self.client.embeddings.create(
                            model=self.embedding_model,
                            input=text,
                            encoding_format="float"
                        )
                        batch_embeddings.append(response.data[0].embedding)
                    except Exception as single_e:
                        print(f"单个文本块处理错误: '{text[:50]}...': {single_e}")
                        batch_embeddings.append([0.0] * self.embedding_dimension)
            
            embeddings.extend(batch_embeddings)
            
            # 更新进度并定期保存检查点（每5个批次保存一次）
            if self.state:
                processed_chunks = len(embeddings)
                self.state.update_progress(
                    processed_chunks=processed_chunks,
                    total_chunks=len(texts),
                    current_batch=processed_chunks,
                    total_batches=total_batches
                )
                
                # 每5个批次保存一次检查点，减少I/O开销
                if batch_index % 5 == 0:
                    self._save_partial_embeddings(embeddings)
                    print(f"检查点已保存 (批次 {batch_index})")
            
            print(f"批次 {batch_index}/{total_batches} 处理完成")
        
        print(f"所有批次处理完成，共处理 {len(embeddings)} 个文本块的embeddings")
        
        # 验证所有embedding维度一致
        for i, emb in enumerate(embeddings):
            if len(emb) != self.embedding_dimension:
                print(f"Warning: Embedding {i} has dimension {len(emb)}, padding/truncating to {self.embedding_dimension}")
                if len(emb) < self.embedding_dimension:
                    emb.extend([0.0] * (self.embedding_dimension - len(emb)))
                else:
                    embeddings[i] = emb[:self.embedding_dimension]
        
        return embeddings
    
    def _save_partial_embeddings(self, embeddings: List[List[float]]):
        """保存部分embeddings到临时文件"""
        if not self.state or not self.state.state.get("embeddings_path"):
            return
        
        embeddings_path = self.state.state["embeddings_path"]
        if embeddings_path:
            try:
                with open(embeddings_path, 'w', encoding='utf-8') as f:
                    json.dump(embeddings, f, ensure_ascii=False)
            except Exception as e:
                print(f"保存embeddings时出错: {e}")
    
    def _load_partial_embeddings(self) -> List[List[float]]:
        """从临时文件加载部分embeddings"""
        if not self.state:
            return []
        
        embeddings_path = self.state.state.get("embeddings_path")
        if embeddings_path and os.path.exists(embeddings_path):
            try:
                with open(embeddings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载embeddings时出错: {e}")
                return []
        return []
    
    @staticmethod
    def _build_annoy_index(embeddings: List[List[float]]) -> AnnoyIndex:
        """构建Annoy索引"""
        if not embeddings:
            raise ValueError("No embeddings to build index")
        
        dimension = len(embeddings[0])
        annoy_index = AnnoyIndex(dimension, 'angular')  # 'angular' is recommended for cosine-based embeddings
        
        for i, vector in enumerate(embeddings):
            annoy_index.add_item(i, vector)
        
        annoy_index.build(10)  # 10棵树，树越多精度越高，但索引越大
        return annoy_index
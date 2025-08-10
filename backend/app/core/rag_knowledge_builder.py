from abc import ABC, abstractmethod
from typing import List
from app.core.document import Document

class KnowledgeBaseBuilder(ABC):
    """知识库构建器接口"""
    
    @abstractmethod
    def build_from_documents(self, documents: List[Document]) -> bool:
        """从文档列表构建知识库"""
        pass
    
    @abstractmethod
    def build_from_directory(self, directory_path: str, recursive: bool = True) -> bool:
        """从目录构建知识库"""
        pass
    
    @abstractmethod
    def save(self, vector_store_path: str) -> bool:
        """保存知识库到指定路径"""
        pass
    
    @abstractmethod
    def load(self, vector_store_path: str) -> bool:
        """从指定路径加载知识库"""
        pass
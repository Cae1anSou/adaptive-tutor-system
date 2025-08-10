from abc import ABC, abstractmethod
from typing import List, Iterator
from app.core.document import Document

class DocumentLoader(ABC):
    """文档加载器接口"""
    
    @abstractmethod
    def load(self, file_path: str) -> Document:
        """加载单个文档"""
        pass
    
    @abstractmethod
    def load_batch(self, file_paths: List[str]) -> List[Document]:
        """批量加载文档"""
        pass
    
    @abstractmethod
    def load_from_directory(self, directory_path: str, recursive: bool = True) -> Iterator[Document]:
        """从目录加载文档"""
        pass
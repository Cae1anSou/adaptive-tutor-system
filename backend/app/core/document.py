from dataclasses import dataclass
from typing import Optional


@dataclass
class Document:
    """文档实体类"""
    id: str
    title: str
    content: str
    file_path: str
    file_type: str  # 'md', 'txt', 'json'
    metadata: Optional[dict] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @property
    def size(self) -> int:
        """返回文档内容的字符数"""
        return len(self.content)

    @property
    def is_valid(self) -> bool:
        """检查文档是否有效"""
        return bool(self.content.strip())

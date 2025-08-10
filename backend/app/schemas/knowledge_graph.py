from pydantic import BaseModel
from typing import List, Dict, Any
from app.schemas.response import StandardResponse

class KnowledgeGraphNodeData(BaseModel):
    """知识图谱节点数据模型
    
    定义知识图谱中单个节点的数据内容，采用Cypher.js兼容格式。
    
    Attributes:
        id: 节点唯一标识符
        label: 节点显示标签
    """
    id: str
    label: str

class KnowledgeGraphNode(BaseModel):
    """知识图谱节点模型
    
    知识图谱中的节点结构，包含节点数据对象。
    这种结构是为了与Cypher.js等图形库兼容。
    
    Attributes:
        data: 节点数据对象，包含id和label信息
    """
    data: KnowledgeGraphNodeData

class KnowledgeGraphEdgeData(BaseModel):
    """知识图谱边数据模型
    
    定义知识图谱中边的连接关系，采用Cypher.js兼容格式。
    
    Attributes:
        source: 源节点ID
        target: 目标节点ID
    """
    source: str
    target: str

class KnowledgeGraphEdge(BaseModel):
    """知识图谱边模型
    
    知识图谱中的边结构，表示节点间的连接关系。
    这种结构是为了与Cypher.js等图形库兼容。
    
    Attributes:
        data: 边数据对象，包含源节点和目标节点信息
    """
    data: KnowledgeGraphEdgeData

class KnowledgeGraph(BaseModel):
    """知识图谱模型
    
    完整的知识图谱结构，包含所有节点和边。
    
    Attributes:
        nodes: 节点列表，包含所有知识点节点
        edges: 边列表，包含所有节点间的连接关系
        dependent_edges: 依赖边列表，包含知识点间的依赖关系
    """
    nodes: List[KnowledgeGraphNode]
    edges: List[KnowledgeGraphEdge]
    dependent_edges: List[KnowledgeGraphEdge]

KnowledgeGraphResponse = StandardResponse[KnowledgeGraph]
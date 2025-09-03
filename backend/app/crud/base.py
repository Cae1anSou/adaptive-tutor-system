from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union, Tuple
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc

# 导入SQLAlchemy模型基类
from app.db.base_class import Base

# 定义泛型类型变量
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

# 定义排序方向枚举
from enum import Enum

class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        具有默认创建、读取、更新、删除（CRUD）操作的CRUD对象。

        **参数**

        * `model`: SQLAlchemy模型类
        """
        self.model = model

    def get(self, db: Session, obj_id: Any) -> Optional[ModelType]:
        """
        通过ID获取单个记录。
        
        Args:
            db: 数据库会话
            obj_id: 记录ID
            
        Returns:
            Optional[ModelType]: 找到的记录，如果不存在则返回None
        """
        # 检查obj_id是否为None，避免在filter中产生无效的布尔值
        if obj_id is None:
            return None
        return db.query(self.model).filter(self.model.id == obj_id).first()  # type: ignore

    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filter_conditions: Optional[Dict[str, Any]] = None,
        sort_by: Optional[Union[str, List[Tuple[str, SortDirection]]]] = None
    ) -> List[ModelType]:
        """
        获取多个记录（支持分页、筛选和排序）。
        
        Args:
            db: 数据库会话
            skip: 跳过的记录数，默认为0
            limit: 返回的记录数限制，默认为100
            filter_conditions: 筛选条件字典，例如 {"participant_id": "user123"}
            sort_by: 排序字段，可以是单个字段名字符串或字段-方向元组列表
            
        Returns:
            List[ModelType]: 记录列表
        """
        query = db.query(self.model)
        
        # 应用筛选条件
        if filter_conditions:
            for field, value in filter_conditions.items():
                if hasattr(self.model, field):
                    # 简单相等筛选
                    query = query.filter(getattr(self.model, field) == value)
        
        # 应用排序
        if sort_by:
            if isinstance(sort_by, str):
                # 单字段排序，默认升序
                query = query.order_by(asc(getattr(self.model, sort_by)))
            elif isinstance(sort_by, list):
                # 多字段排序
                for field, direction in sort_by:
                    if hasattr(self.model, field):
                        column = getattr(self.model, field)
                        if direction == SortDirection.DESC:
                            query = query.order_by(desc(column))
                        else:
                            query = query.order_by(asc(column))
        
        # 应用分页
        sql = query.statement.compile(compile_kwargs={"literal_binds": True})
        print("最终生成的 SQL:", sql)
        
        # 应用分页
        return query.offset(skip).limit(limit).all()

    def get_count(
        self, 
        db: Session, 
        *, 
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        获取符合条件的记录总数。
        
        Args:
            db: 数据库会话
            filter_conditions: 筛选条件字典，例如 {"participant_id": "user123"}
            
        Returns:
            int: 符合条件的记录总数
        """
        query = db.query(self.model)
        
        # 应用筛选条件
        if filter_conditions:
            for field, value in filter_conditions.items():
                if hasattr(self.model, field):
                    # 简单相等筛选
                    query = query.filter(getattr(self.model, field) == value)
        
        return query.count()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """
        创建一个新的记录。
        
        Args:
            db: 数据库会话
            obj_in: 创建记录的数据对象
            
        Returns:
            ModelType: 创建的记录
        """
        # 使用fastapi的jsonable_encoder，确保数据可被序列化
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)  # SQLAlchemy model
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def update(
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        更新一个已存在的记录。
        
        Args:
            db: 数据库会话
            db_obj: 要更新的数据库对象
            obj_in: 更新数据对象，可以是UpdateSchemaType或字典
            
        Returns:
            ModelType: 更新后的记录
        """
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            # exclude_unset=True 表示只获取被显式设置了值的字段
            update_data = obj_in.model_dump(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
                
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, obj_id: int) -> Optional[ModelType]:
        """
        删除一个记录。
        
        Args:
            db: 数据库会话
            obj_id: 要删除的记录ID
            
        Returns:
            Optional[ModelType]: 被删除的记录，如果不存在则返回None
        """
        obj = db.query(self.model).get(obj_id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

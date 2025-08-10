from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

# 导入SQLAlchemy模型基类
from app.db.base_class import Base

# 定义泛型类型变量
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


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
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """
        获取多个记录（支持分页）。
        
        Args:
            db: 数据库会话
            skip: 跳过的记录数，默认为0
            limit: 返回的记录数限制，默认为100
            
        Returns:
            List[ModelType]: 记录列表
        """
        return db.query(self.model).offset(skip).limit(limit).all()

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
        obj_in_data = jsonable_encoder(obj_in)
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

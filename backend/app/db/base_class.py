from sqlalchemy.ext.declarative import declarative_base

# 创建一个统一的Base类，所有模型都应该继承这个类
Base = declarative_base()
# This file makes the 'models' directory a Python package.
from sqlalchemy.ext.declarative import declarative_base

# 创建统一的 Base 类，供所有模型使用
Base = declarative_base()

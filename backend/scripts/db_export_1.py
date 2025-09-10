import json
import pymysql
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# 数据库连接配置
DATABASE_URL = "mysql+pymysql://caelan:Silvis0852.@8.136.48.153:3306/ai_exp"


def export_database_to_json():
    # 创建数据库引擎
    engine = create_engine(DATABASE_URL)

    # 创建检查器来获取表信息
    inspector = inspect(engine)

    # 获取所有表名
    table_names = inspector.get_table_names()

    # 创建会话
    Session = sessionmaker(bind=engine)
    session = Session()

    result = {}

    try:
        for table_name in table_names:
            # 获取表结构
            columns = inspector.get_columns(table_name)

            # 查询表数据
            query = text(f"SELECT * FROM {table_name}")
            rows = session.execute(query).fetchall()

            # 转换为字典列表
            table_data = []
            for row in rows:
                row_dict = {}
                for i, column in enumerate(columns):
                    row_dict[column['name']] = row[i]
                table_data.append(row_dict)

            result[table_name] = {
                'columns': [col['name'] for col in columns],
                'data': table_data
            }

            print(f"导出表 {table_name}: {len(table_data)} 行数据")

    finally:
        session.close()

    # 保存为JSON文件
    with open('ai_exp_database_export.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    print("数据库导出完成！")


if __name__ == "__main__":
    export_database_to_json()
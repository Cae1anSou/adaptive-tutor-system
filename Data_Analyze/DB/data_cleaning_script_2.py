import json
from collections import defaultdict
from datetime import datetime

def convert_to_timestamp(date_str):
    """
    将日期字符串转换为时间戳（秒）
    """
    if not date_str:
        return None
    
    try:
        # 处理不同的日期格式
        if ' ' in date_str:
            # 格式: "YYYY-MM-DD HH:MM:SS"
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        else:
            # 格式: "YYYY-MM-DD"
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        
        # 转换为时间戳（秒）
        timestamp = int(dt.timestamp())
        return timestamp
    except ValueError:
        # 如果转换失败，返回原始值
        return date_str

def clean_and_group_data(input_file, output_file):
    """
    按participant_id分组清洗数据集
    键是用户的participant_id,值是该用户在所有数据表中的数据
    时间字段转换为时间戳格式
    只保留participant_id为baseline0或exp0开头的用户数据
    忽略在忽略列表中的participant_id
    """
    # 读取JSON数据
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 创建一个字典来存储按participant_id分组的数据
    grouped_data = defaultdict(list)
    
    # 定义需要忽略的participant_id列表
    ignored_participant_ids = set([
        # 在这里添加需要忽略的participant_id
        # 例如: 'test_user', 'dev_user', 等等
        'exp001',
        'baseline002',
        'exp002',
        'exp003',
        'exp004'
        'baseline003',
        'exp004'
    ])
    
    # 需要转换为时间戳的字段名
    timestamp_fields = ['timestamp', 'created_at', 'completed_at', 'submitted_at']
    
    # 遍历所有表
    for table_name, table_content in data.items():
        columns = table_content['columns']
        rows = table_content['data']
        
        # 检查表中是否有participant_id列
        if 'participant_id' in columns:
            # 遍历每一行数据
            for row in rows:
                # 获取participant_id值
                # 处理不同的数据格式（字典或列表）
                if isinstance(row, dict):
                    participant_id = row.get('participant_id')
                else:
                    # 如果是列表格式，需要找到participant_id的索引
                    participant_id_index = columns.index('participant_id')
                    participant_id = row[participant_id_index] if participant_id_index < len(row) else None
                
                # 只处理以baseline0或exp0开头的用户数据，并且不在忽略列表中
                if (participant_id is not None and 
                    (participant_id.startswith('baseline0') or participant_id.startswith('exp0')) and
                    participant_id not in ignored_participant_ids):
                    # 在每条记录中添加表名信息
                    if isinstance(row, dict):
                        row_with_table = row.copy()
                    else:
                        # 如果是列表格式，转换为字典格式
                        row_with_table = dict(zip(columns, row))
                    
                    # 添加表名信息
                    row_with_table['_table'] = table_name
                    
                    # 转换时间字段为时间戳
                    for field in timestamp_fields:
                        if field in row_with_table and row_with_table[field]:
                            row_with_table[field] = convert_to_timestamp(row_with_table[field])
                    
                    # 添加行数据到对应用户
                    grouped_data[participant_id].append(row_with_table)
        else:
            print(f"表 '{table_name}' 没有 participant_id 列，跳过该表的处理")
    
    # 将defaultdict转换为普通字典
    grouped_data = dict(grouped_data)
    
    # 保存清洗后的数据到新文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(grouped_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"数据清洗完成！共处理了 {len(grouped_data)} 个不同的participant_id")
    return grouped_data

def print_summary(grouped_data):
    """
    打印数据摘要
    """
    print("\n数据摘要:")
    print(f"总用户数: {len(grouped_data)}")
    
    # 显示每个用户的数据统计
    for participant_id, records in grouped_data.items():
        print(f"用户 '{participant_id}': {len(records)} 条记录")

if __name__ == "__main__":
    input_file = 'ai_exp_database_export.json'
    output_file = '按id分.json'
    
    # 执行数据清洗和分组
    grouped_data = clean_and_group_data(input_file, output_file)
    
    # 打印摘要
    print_summary(grouped_data)
    
    print(f"\n清洗后的数据已保存到: {output_file}")
import json

def filter_essential_data(input_file, output_file):
    """
    进一步清洗数据，只保留以下三类数据：
    1. 学习进度（user_progress）
    2. 提交（submissions）
    3. 对话（chat_history）
    """
    # 读取已清洗的数据
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 定义需要保留的表
    essential_tables = {'user_progress', 'submissions', 'chat_history'}
    
    # 创建新的字典来存储过滤后的数据
    filtered_data = {}
    
    # 统计信息
    total_users = len(data)
    kept_users = 0
    total_records = 0
    kept_records = 0
    
    # 遍历每个用户
    for participant_id, records in data.items():
        total_records += len(records)
        
        # 过滤出需要保留的记录
        essential_records = [
            record for record in records 
            if record.get('_table') in essential_tables
        ]
        
        # 如果该用户有过滤后的记录，则保留该用户
        if essential_records:
            filtered_data[participant_id] = essential_records
            kept_users += 1
            kept_records += len(essential_records)
    
    # 保存过滤后的数据到新文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=2, default=str)
    
    # 打印统计信息
    print(f"数据过滤完成！")
    print(f"原始用户数: {total_users}")
    print(f"保留用户数: {kept_users}")
    print(f"原始记录数: {total_records}")
    print(f"保留记录数: {kept_records}")
    
    # 统计各类数据的数量
    table_counts = {}
    for participant_id, records in filtered_data.items():
        for record in records:
            table = record.get('_table')
            if table in table_counts:
                table_counts[table] += 1
            else:
                table_counts[table] = 1
    
    print("\n各类数据统计:")
    for table, count in table_counts.items():
        print(f"  {table}: {count} 条记录")
    
    return filtered_data

def print_sample_data(filtered_data, sample_user=None):
    """
    打印示例数据
    """
    if not filtered_data:
        print("没有数据可显示")
        return
    
    # 如果没有指定用户，选择第一个用户
    if sample_user is None:
        sample_user = list(filtered_data.keys())[0]
    
    if sample_user not in filtered_data:
        print(f"用户 '{sample_user}' 不存在")
        return
    
    print(f"\n用户 '{sample_user}' 的示例数据:")
    records = filtered_data[sample_user]
    
    # 按表分组显示
    table_groups = {}
    for record in records:
        table = record.get('_table', 'unknown')
        if table not in table_groups:
            table_groups[table] = []
        table_groups[table].append(record)
    
    for table, table_records in table_groups.items():
        print(f"  {table}: {len(table_records)} 条记录")
        # 显示第一条记录作为示例
        if table_records:
            print(f"    示例: {str(table_records[0])[:100]}...")

if __name__ == "__main__":
    input_file = '按id分.json'
    output_file = 'for老师.json'
    
    # 执行数据过滤
    filtered_data = filter_essential_data(input_file, output_file)
    
    # 打印示例数据
    print_sample_data(filtered_data)
    
    print(f"\n过滤后的核心数据已保存到: {output_file}")
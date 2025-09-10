import json

def filter_essential_data(input_file, output_file):
    """
    进一步清洗数据，按以下结构整理：
    {
      "baseline001": {
        "assistant_token_num":0,
        "pass_rate_avg":0,
        "debug_dur_avg":0,
        "topic_pass": [],
        "topic_try_num":{"1_1":3, "1_3":5},
        "topic_debug_dur":{"1_1":20000, "1_3":30000},
        "emotion": [
          ["12334534", "1.1234", "1.345345", "hello"]
        ]
      }
    }
    """
    # 读取已清洗的数据
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 创建新的字典来存储过滤后的数据
    filtered_data = {}
    
    # 统计信息
    total_users = len(data)
    kept_users = 0
    
    for participant_id, records in data.items():
        # 按表类型分类数据
        chat_history = []
        user_progress = []
        submissions = []
        
        for record in records:
            table = record.get('_table')
            if table == 'chat_history':
                chat_history.append(record)
            elif table == 'user_progress':
                user_progress.append(record)
            elif table == 'submissions':
                submissions.append(record)
        
        # 计算各个字段
        user_data = {}
        
        # 1. assistant_token_num：统计所有assistant角色的complete_tokens总和
        assistant_token_num = 0
        for record in chat_history:
            if record.get('role') == 'assistant' and record.get('completion_tokens'):
                assistant_token_num += record.get('completion_tokens', 0)
        user_data['assistant_token_num'] = assistant_token_num
        
        # 2. topic_pass：从progress表中获取用户通过的topic列表
        topic_pass = []
        for record in user_progress:
            if record.get('completed_at'):  # 如果有completed_at字段，说明用户通过了这个topic
                topic_pass.append(record.get('topic_id'))
        user_data['topic_pass'] = topic_pass
        
        # 3. topic_try_num：从submission表中统计每个topic的尝试次数
        topic_try_num = {}
        for record in submissions:
            topic_id = record.get('topic_id')
            if topic_id:
                topic_try_num[topic_id] = topic_try_num.get(topic_id, 0) + 1
        user_data['topic_try_num'] = topic_try_num
        
        # 4. topic_debug_dur：计算每个topic的调试持续时间和通过状态
        topic_debug_dur = {}
        
        # 找出每个topic的第一次和最后一次submission时间
        topic_submissions = {}
        for record in submissions:
            topic_id = record.get('topic_id')
            timestamp = record.get('submitted_at')  # 使用submitted_at字段
            if topic_id and timestamp:
                if topic_id not in topic_submissions:
                    topic_submissions[topic_id] = []
                topic_submissions[topic_id].append(timestamp)
        
        # 找出所有topic中开始最迟的（最后一个尝试的topic）
        latest_start_topic = None
        latest_start_time = 0
        for topic_id, timestamps in topic_submissions.items():
            first_submission = min(timestamps)
            if first_submission > latest_start_time:
                latest_start_time = first_submission
                latest_start_topic = topic_id
        
        # 计算每个topic的调试持续时间和通过状态
        for topic_id, timestamps in topic_submissions.items():
            first_submission = min(timestamps)
            last_submission = max(timestamps)
            
            # 检查是否通过
            is_passed = topic_id in topic_pass
            
            # 特殊情况处理：如果是因时间到而未通过的最后一个topic，不计入
            if not is_passed and topic_id == latest_start_topic:
                continue
            
            duration = (last_submission - first_submission) * 1000  # 转换为毫秒
            topic_debug_dur[topic_id] = duration
        
        user_data['topic_debug_dur'] = topic_debug_dur
        
        # 5. pass_rate_avg：计算尝试通过率（通过的topic数 / 总提交次数）
        total_attempts = sum(topic_try_num.values())  # 总提交次数
        passed_topics = len(topic_pass)  # 通过的topic数量
        
        if total_attempts > 0:
            pass_rate_avg = passed_topics / total_attempts
        else:
            pass_rate_avg = 0.0
        user_data['pass_rate_avg'] = pass_rate_avg
        
        # 6. debug_dur_avg：计算topic_debug_duration的平均值
        if topic_debug_dur:
            debug_dur_avg = sum(topic_debug_dur.values()) / len(topic_debug_dur)
        else:
            debug_dur_avg = 0.0
        user_data['debug_dur_avg'] = debug_dur_avg
        
        # 保留timestamp、bert、k_means等字段（如果存在）
        if records:
            # 从第一条记录中获取可能的额外字段
            sample_record = records[0]
            if 'timestamp' in sample_record:
                user_data['timestamp'] = [r.get('timestamp') for r in records if r.get('timestamp')]
            if 'bert' in sample_record:
                user_data['bert'] = [r.get('bert') for r in records if r.get('bert')]
            if 'k_means' in sample_record:
                user_data['k_means'] = [r.get('k_means') for r in records if r.get('k_means')]
        
        filtered_data[participant_id] = user_data
        kept_users += 1

    # 保存过滤后的数据到新文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, ensure_ascii=False, indent=2, default=str)
    
    # 打印统计信息
    print(f"数据整理完成！")
    print(f"原始用户数: {total_users}")
    print(f"处理用户数: {kept_users}")
    
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
    
    print(f"\n用户 '{sample_user}' 的整理后数据:")
    user_data = filtered_data[sample_user]
    
    # 显示各个字段
    for key, value in user_data.items():
        if isinstance(value, list) and len(value) > 3:
            print(f"  {key}: {value[:3]}... (共{len(value)}项)")
        elif isinstance(value, dict) and len(value) > 3:
            print(f"  {key}: {dict(list(value.items())[:3])}... (共{len(value)}项)")
        else:
            print(f"  {key}: {value}")

if __name__ == "__main__":
    input_file = 'for老师.json'
    output_file = 'for老师_final.json'
    
    # 执行数据过滤
    filtered_data = filter_essential_data(input_file, output_file)
    
    # 打印示例数据
    print_sample_data(filtered_data)
    
    print(f"\n过滤后的核心数据已保存到: {output_file}")
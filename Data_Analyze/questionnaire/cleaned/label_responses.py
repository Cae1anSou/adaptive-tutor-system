import pandas as pd

def add_labels_to_response(row):
    if pd.isna(row['response']):
        return ''
    response = str(row['response']).lower()
    module = row['module']
    question_type = row['question_type']

    labels = []

    # 兴趣生成模块标签
    if module == 'interest_generation':
        if question_type == 'advantage':
            if any(word in response for word in ['interest', 'enjoyable', 'motivation', 'engaged', 'fun', 'like', 'prefer']):
                labels.extend(['兴趣驱动', '提升学习兴趣'])
            if any(word in response for word in ['choose', 'option', 'freedom', 'flexibility', 'personal']):
                labels.extend(['个性化学习', '选择自由'])
            if any(word in response for word in ['content', 'rich', 'detailed', 'comprehensive']):
                labels.append('内容丰富')
            if any(word in response for word in ['creative', 'helpful', 'useful']):
                labels.append('创意设计')

        elif question_type == 'difficulty':
            if any(word in response for word in ['crowded', 'small screen', 'resolution', 'layout']):
                labels.append('界面布局问题')
            if any(word in response for word in ['code', 'long', 'scroll', 'troublesome']):
                labels.append('代码显示问题')
            if any(word in response for word in ['slow', 'speed', 'loading']):
                labels.append('性能问题')
            if any(word in response for word in ['complex', 'difficult', 'confusing']):
                labels.append('使用复杂性')
            if 'no' in response or 'none' in response:
                labels.append('无困难')

        elif question_type == 'suggestion':
            if any(word in response for word in ['more options', 'expand', 'variety']):
                labels.append('增加选项')
            if any(word in response for word in ['difficulty', 'level', 'adjust']):
                labels.append('难度调节')
            if any(word in response for word in ['layout', 'design', 'interface']):
                labels.append('界面优化')
            if any(word in response for word in ['speed', 'performance', 'optimize']):
                labels.append('性能优化')
            if any(word in response for word in ['code', 'copy', 'format']):
                labels.append('代码功能')

    # 开放式探索模块标签
    elif module == 'open_exploration':
        if question_type == 'advantage':
            if any(word in response for word in ['freedom', 'flexible', 'creativity', 'choose']):
                labels.extend(['自由探索', '创造性思维'])
            if any(word in response for word in ['understand', 'implementation', 'practical']):
                labels.append('实践理解')
            if any(word in response for word in ['beginner', 'easy', 'intuitive']):
                labels.append('新手友好')

        elif question_type == 'difficulty':
            if any(word in response for word in ['small', 'window', 'read', 'difficult']):
                labels.append('显示尺寸问题')
            if any(word in response for word in ['broad', 'unfocused', 'guidance']):
                labels.append('缺乏指导')
            if any(word in response for word in ['limited', 'css', 'javascript']):
                labels.append('功能限制')

        elif question_type == 'suggestion':
            if any(word in response for word in ['professional', 'advanced']):
                labels.append('专业性提升')
            if any(word in response for word in ['guidance', 'highlight', 'structure']):
                labels.append('增加指导')
            if any(word in response for word in ['resize', 'drag', 'interface']):
                labels.append('界面改进')

    # 渐进式知识展开模块标签
    elif module == 'progressive_unfolding':
        if question_type == 'advantage':
            if any(word in response for word in ['step by step', 'gradual', 'progressive', 'level']):
                labels.extend(['循序渐进', '分步学习'])
            if any(word in response for word in ['cognitive', 'load', 'easy', 'simple']):
                labels.append('降低认知负荷')
            if any(word in response for word in ['understand', 'complex', 'manageable']):
                labels.append('复杂概念理解')

        elif question_type == 'difficulty':
            if any(word in response for word in ['slow', 'pace', 'advanced']):
                labels.append('进度问题')
            if any(word in response for word in ['loading', 'fail', 'network']):
                labels.append('技术问题')
            if any(word in response for word in ['compact', 'crowded', 'long text']):
                labels.append('界面布局问题')

        elif question_type == 'suggestion':
            if any(word in response for word in ['pacing', 'speed', 'personal']):
                labels.append('个性化进度')
            if any(word in response for word in ['streamline', 'concise', 'simplify']):
                labels.append('内容优化')
            if any(word in response for word in ['loading', 'performance']):
                labels.append('性能优化')

    # 编程模块标签
    elif module == 'programming_module':
        if question_type == 'advantage':
            if any(word in response for word in ['real time', 'immediate', 'preview', 'instant']):
                labels.extend(['实时预览', '即时反馈'])
            if any(word in response for word in ['completion', 'suggestion', 'intelligent']):
                labels.extend(['代码补全', '智能辅助'])
            if any(word in response for word in ['error', 'check', 'debug']):
                labels.append('错误检测')
            if any(word in response for word in ['practice', 'test', 'exercise']):
                labels.append('实践练习')

        elif question_type == 'difficulty':
            if any(word in response for word in ['completion', 'close tag', 'assistant']):
                labels.append('代码辅助不完善')
            if any(word in response for word in ['switch', 'memory', 'reset']):
                labels.append('用户体验问题')
            if any(word in response for word in ['evaluation', 'unclear', 'requirements']):
                labels.append('测试问题')

        elif question_type == 'suggestion':
            if any(word in response for word in ['file tree', 'multiple files']):
                labels.append('文件管理')
            if any(word in response for word in ['close tag', 'completion']):
                labels.append('代码辅助改进')
            if any(word in response for word in ['memory', 'save', 'persistent']):
                labels.append('数据持久化')
            if any(word in response for word in ['layout', 'side by side']):
                labels.append('界面布局')

    # AI教学助手模块标签
    elif module == 'ai_teaching_assistant':
        if question_type == 'advantage':
            if any(word in response for word in ['guidance', 'guide', 'step by step', 'patience']):
                labels.extend(['引导式教学', '耐心指导'])
            if any(word in response for word in ['immediate', 'instant', 'anytime', 'available']):
                labels.append('即时帮助')
            if any(word in response for word in ['context', 'aware', 'detect']):
                labels.append('上下文感知')
            if any(word in response for word in ['convenient', 'switch', 'page']):
                labels.append('便利性')

        elif question_type == 'difficulty':
            if any(word in response for word in ['copy', 'paste', 'manual', 'troublesome']):
                labels.append('交互不便')
            if any(word in response for word in ['slow', 'lag', 'response time']):
                labels.append('响应速度慢')
            if any(word in response for word in ['generic', 'general', 'not specific']):
                labels.append('回答不够精准')
            if any(word in response for word in ['terminology', 'professional', 'beginner']):
                labels.append('术语过于专业')

        elif question_type == 'suggestion':
            if any(word in response for word in ['access code', 'read compiler', 'automatic']):
                labels.append('代码集成')
            if any(word in response for word in ['streaming', 'flow', 'progressive']):
                labels.append('流式输出')
            if any(word in response for word in ['context', 'memory', 'awareness']):
                labels.append('上下文记忆')
            if any(word in response for word in ['adaptive', 'level', 'personalized']):
                labels.append('自适应调整')

    return ','.join(labels) if labels else ''

# 读取CSV文件
df = pd.read_csv('/Users/caoxinzhuo/code/CHI26/adaptive-tutor-system/Data_Analyze/questionnaire/cleaned/module_feedback_long.csv')

# 在module列后插入tips列
df.insert(3, 'tips', '')

# 应用标签函数
df['tips'] = df.apply(add_labels_to_response, axis=1)

# 保存更新后的文件
df.to_csv('/Users/caoxinzhuo/code/CHI26/adaptive-tutor-system/Data_Analyze/questionnaire/cleaned/module_feedback_long.csv', index=False)

print("标签添加完成！")

# 统计标签使用情况
all_labels = []
for tips in df['tips']:
    if tips:
        all_labels.extend(tips.split(','))

from collections import Counter
label_counts = Counter(all_labels)

print("\n标签使用统计：")
for label, count in label_counts.most_common():
    print(f"{label}: {count}次")
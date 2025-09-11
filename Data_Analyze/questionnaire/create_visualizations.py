import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def load_data():
    """加载JSON数据"""
    with open('Data_Analyze/questionnaire/survey_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def is_valid_number(value):
    """检查值是否为有效的数字"""
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return not (isinstance(value, float) and np.isnan(value))
    if str(value).replace('.', '').isdigit():
        return True
    return False

def create_sus_visualization(data):
    """创建SUS量表可视化图表"""
    # SUS量表题目
    sus_items = [
        "I think that I would like to use this system frequently.  ",
        "I found the system unnecessarily complex.  ",
        "I thought the system was easy to use. ",
        "I think that I would need the support of a technical person to be able to use this system. ",
        "I found the various functions in this system were well integrated. ",
        "I thought there was too much inconsistency in this system. ",
        "I would imagine that most people would learn to use this system very quickly. ",
        "I found the system very cumbersome to use. ",
        "I felt very confident using the system. ",
        "I needed to learn a lot of things before I could get going with this system. "
    ]
    
    # 提取有效数据
    valid_sus_scores = []
    for participant in data:
        raw_scores = []
        valid = True
        for item in sus_items:
            score = participant.get(item)
            if is_valid_number(score):
                raw_scores.append(int(float(score)))
            else:
                valid = False
                break
        
        if valid and len(raw_scores) == 10:
            # 计算SUS分数
            converted_scores = []
            for i, score in enumerate(raw_scores):
                if i % 2 == 0:  # 奇数题
                    converted_scores.append(score - 1)
                else:  # 偶数题
                    converted_scores.append(5 - score)
            
            total_score = sum(converted_scores)
            sus_score = total_score * 2.5
            valid_sus_scores.append(sus_score)
    
    # 创建SUS分数分布图
    plt.figure(figsize=(10, 6))
    plt.hist(valid_sus_scores, bins=8, color='skyblue', edgecolor='black', alpha=0.7)
    plt.axvline(np.mean(valid_sus_scores), color='red', linestyle='--', linewidth=2, 
                label=f'平均分: {np.mean(valid_sus_scores):.2f}')
    plt.axvline(68, color='orange', linestyle='-', linewidth=2, 
                label='行业平均线 (68)')
    
    plt.xlabel('SUS分数')
    plt.ylabel('频数')
    plt.title('System Usability Scale (SUS) 分数分布')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('Data_Analyze/questionnaire/sus_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_nasa_tlx_visualization(data):
    """创建NASA-TLX量表可视化图表"""
    # NASA-TLX量表题目
    nasa_items = [
        "  How much mental and perceptual activity was required (e.g., thinking, deciding, calculating, remembering, looking, searching, etc.)?  ",
        "How much physical activity was required (e.g., pushing, pulling, turning, controlling, activating, etc.)? ",
        "How much time pressure did you feel due to the rate or pace at which the tasks occurred? ",
        "How successful do you think you were in accomplishing the goals of the task set by the experimenter (or yourself)? How satisfied were you with your performance in accomplishing these goals? ",
        "How hard did you have to work (mentally and physically) to accomplish your level of performance? ",
        "How insecure, discouraged, irritated, stressed, and annoyed versus secure, gratified, content, relaxed, and complacent did you feel during the task? "
    ]
    
    dimension_names = [
        "Mental\nDemand",
        "Physical\nDemand", 
        "Temporal\nDemand",
        "Performance",
        "Effort",
        "Frustration"
    ]
    
    # 提取数据
    dimension_scores = {name: [] for name in dimension_names}
    for participant in data:
        for i, item in enumerate(nasa_items):
            score = participant.get(item)
            if is_valid_number(score):
                dimension_scores[dimension_names[i]].append(int(float(score)))
    
    # 创建NASA-TLX雷达图
    plt.figure(figsize=(10, 8))
    angles = np.linspace(0, 2 * np.pi, len(dimension_names), endpoint=False).tolist()
    angles += angles[:1]  # 闭合图形
    
    ax = plt.subplot(111, projection='polar')
    
    # 计算各维度平均分
    mean_scores = []
    for name in dimension_names:
        scores = dimension_scores[name]
        if scores:
            mean_scores.append(np.mean(scores))
        else:
            mean_scores.append(0)
    mean_scores += mean_scores[:1]  # 闭合图形
    
    ax.plot(angles, mean_scores, 'o-', linewidth=2, color='blue', label='平均分')
    ax.fill(angles, mean_scores, alpha=0.25, color='blue')
    
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dimension_names)
    ax.set_ylim(0, 20)
    ax.set_title('NASA Task Load Index (NASA-TLX) 雷达图', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
    
    plt.tight_layout()
    plt.savefig('Data_Analyze/questionnaire/nasa_tlx_radar.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 创建NASA-TLX柱状图
    plt.figure(figsize=(12, 6))
    mean_values = [np.mean(dimension_scores[name]) if dimension_scores[name] else 0 for name in dimension_names]
    std_values = [np.std(dimension_scores[name], ddof=1) if len(dimension_scores[name]) > 1 else 0 for name in dimension_names]
    
    bars = plt.bar(dimension_names, mean_values, yerr=std_values, capsize=5, 
                   color='lightcoral', edgecolor='black', alpha=0.7)
    
    # 在柱状图上添加数值标签
    for bar, value in zip(bars, mean_values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                 f'{value:.2f}', ha='center', va='bottom')
    
    plt.ylabel('平均分 (0-20)')
    plt.title('NASA Task Load Index (NASA-TLX) 各维度得分')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('Data_Analyze/questionnaire/nasa_tlx_bar.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_cps_visualization(data):
    """创建编程自我效能感量表可视化图表"""
    # 四个维度的题目
    dimensions = {
        "Programming Logic\n& Understanding": [
            "  I can understand the basic logical structure of HTML, CSS, and JavaScript code.  ",
            "  I can understand how conditional statements (e.g., if...else) work with AI support.  ",
            "I can predict the result of a JavaScript program when given specific input values. "
        ],
        "Debugging &\nProblem Solving": [
            "  I can identify and correct errors in my HTML, CSS, or JavaScript code with the help of AI.  ",
            "I can understand error messages and AI-generated explanations when my code does not run correctly. ",
            "I can improve my programming skills by learning from AI debugging suggestions. "
        ],
        "Code Writing\n& Application": [
            "I can write a simple web page using HTML, CSS, and JavaScript with AI guidance. ",
            "I can use AI to help me apply loops, conditions, or functions in JavaScript. ",
            "I can combine AI suggestions with my own knowledge to solve a programming task. "
        ],
        "Confidence &\nCollaboration": [
            "I feel confident that I can complete programming exercises with AI support. ",
            "I believe I can continue learning web development effectively with AI assistance. ",
            "I can work more efficiently by dividing tasks between myself and AI (e.g., I focus on design, AI helps with debugging). "
        ]
    }
    
    # 提取数据
    dimension_scores = {name: [] for name in dimensions.keys()}
    overall_scores = []
    
    for participant in data:
        participant_dimension_scores = {}
        for dim_name, items in dimensions.items():
            dim_scores = []
            for item in items:
                score = participant.get(item)
                if is_valid_number(score) and not (isinstance(score, float) and np.isnan(score)):
                    dim_scores.append(float(score))
            
            if dim_scores:
                dim_mean = np.mean(dim_scores)
                dimension_scores[dim_name].append(dim_mean)
                participant_dimension_scores[dim_name] = dim_mean
            else:
                participant_dimension_scores[dim_name] = None
        
        # 计算总体得分
        valid_dim_scores = [score for score in participant_dimension_scores.values() if score is not None]
        if valid_dim_scores:
            overall_score = np.mean(valid_dim_scores)
            overall_scores.append(overall_score)
    
    # 创建编程自我效能感柱状图
    plt.figure(figsize=(12, 6))
    dimension_names = list(dimensions.keys())
    mean_values = [np.mean(dimension_scores[name]) if dimension_scores[name] else 0 for name in dimension_names]
    std_values = [np.std(dimension_scores[name], ddof=1) if len(dimension_scores[name]) > 1 else 0 for name in dimension_names]
    
    bars = plt.bar(dimension_names, mean_values, yerr=std_values, capsize=5, 
                   color='lightgreen', edgecolor='black', alpha=0.7)
    
    # 在柱状图上添加数值标签
    for bar, value in zip(bars, mean_values):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                 f'{value:.2f}', ha='center', va='bottom')
    
    plt.ylabel('平均分 (1-5)')
    plt.title('编程自我效能感各维度得分')
    plt.ylim(0, 5)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('Data_Analyze/questionnaire/cps_bar.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 创建总体编程自我效能感分布图
    plt.figure(figsize=(10, 6))
    plt.hist(overall_scores, bins=8, color='lightgreen', edgecolor='black', alpha=0.7)
    plt.axvline(np.mean(overall_scores), color='red', linestyle='--', linewidth=2, 
                label=f'平均分: {np.mean(overall_scores):.2f}')
    
    plt.xlabel('编程自我效能感总分')
    plt.ylabel('频数')
    plt.title('编程自我效能感总体分布')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('Data_Analyze/questionnaire/cps_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_correlation_heatmap(data):
    """创建相关性热力图"""
    # 提取所有数值型数据
    sus_items = [
        "I think that I would like to use this system frequently.  ",
        "I found the system unnecessarily complex.  ",
        "I thought the system was easy to use. ",
        "I think that I would need the support of a technical person to be able to use this system. ",
        "I found the various functions in this system were well integrated. ",
        "I thought there was too much inconsistency in this system. ",
        "I would imagine that most people would learn to use this system very quickly. ",
        "I found the system very cumbersome to use. ",
        "I felt very confident using the system. ",
        "I needed to learn a lot of things before I could get going with this system. "
    ]
    
    nasa_items = [
        "  How much mental and perceptual activity was required (e.g., thinking, deciding, calculating, remembering, looking, searching, etc.)?  ",
        "How much physical activity was required (e.g., pushing, pulling, turning, controlling, activating, etc.)? ",
        "How much time pressure did you feel due to the rate or pace at which the tasks occurred? ",
        "How successful do you think you were in accomplishing the goals of the task set by the experimenter (or yourself)? How satisfied were you with your performance in accomplishing these goals? ",
        "How hard did you have to work (mentally and physically) to accomplish your level of performance? ",
        "How insecure, discouraged, irritated, stressed, and annoyed versus secure, gratified, content, relaxed, and complacent did you feel during the task? "
    ]
    
    cps_items = [
        "  I can understand the basic logical structure of HTML, CSS, and JavaScript code.  ",
        "  I can understand how conditional statements (e.g., if...else) work with AI support.  ",
        "I can predict the result of a JavaScript program when given specific input values. ",
        "  I can identify and correct errors in my HTML, CSS, or JavaScript code with the help of AI.  ",
        "I can understand error messages and AI-generated explanations when my code does not run correctly. ",
        "I can improve my programming skills by learning from AI debugging suggestions. ",
        "I can write a simple web page using HTML, CSS, and JavaScript with AI guidance. ",
        "I can use AI to help me apply loops, conditions, or functions in JavaScript. ",
        "I can combine AI suggestions with my own knowledge to solve a programming task. ",
        "I feel confident that I can complete programming exercises with AI support. ",
        "I believe I can continue learning web development effectively with AI assistance. ",
        "I can work more efficiently by dividing tasks between myself and AI (e.g., I focus on design, AI helps with debugging). "
    ]
    
    # 构建数据矩阵
    all_items = sus_items + nasa_items + cps_items
    item_labels = ['SUS' + str(i+1) for i in range(len(sus_items))] + \
                  ['NASA' + str(i+1) for i in range(len(nasa_items))] + \
                  ['CPS' + str(i+1) for i in range(len(cps_items))]
    
    # 提取有效数据
    valid_data = []
    valid_participants = []
    
    for participant in data:
        row = []
        valid = True
        for item in all_items:
            score = participant.get(item)
            if is_valid_number(score) and not (isinstance(score, float) and np.isnan(score)):
                row.append(float(score))
            else:
                valid = False
                break
        
        if valid and len(row) == len(all_items):
            valid_data.append(row)
            valid_participants.append(participant)
    
    if len(valid_data) > 1:
        # 计算相关性矩阵
        data_matrix = np.array(valid_data)
        correlation_matrix = np.corrcoef(data_matrix.T)
        
        # 创建热力图
        plt.figure(figsize=(20, 16))
        sns.heatmap(correlation_matrix, 
                    xticklabels=item_labels, 
                    yticklabels=item_labels,
                    cmap='RdYlBu_r', 
                    center=0,
                    square=True,
                    fmt='.2f',
                    cbar_kws={"shrink": .8})
        
        plt.title('量表题目相关性热力图')
        plt.xticks(rotation=90)
        plt.yticks(rotation=0)
        plt.tight_layout()
        plt.savefig('Data_Analyze/questionnaire/correlation_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()

def main():
    """主函数"""
    # 加载数据
    data = load_data()
    print(f"总共 {len(data)} 份问卷数据")
    
    # 创建可视化图表
    print("正在创建SUS量表可视化图表...")
    create_sus_visualization(data)
    
    print("正在创建NASA-TLX量表可视化图表...")
    create_nasa_tlx_visualization(data)
    
    print("正在创建编程自我效能感量表可视化图表...")
    create_cps_visualization(data)
    
    print("正在创建相关性热力图...")
    create_correlation_heatmap(data)
    
    print("所有可视化图表已生成并保存到 Data_Analyze/questionnaire/ 目录下")

if __name__ == "__main__":
    main()
import json
import numpy as np
from scipy.stats import skew, kurtosis

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

def analyze_sus(data):
    """分析System Usability Scale (SUS)数据"""
    print("=" * 50)
    print("System Usability Scale (SUS) 分析")
    print("=" * 50)
    
    # SUS量表题目 (10个题目)
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
    
    sus_scores = []
    missing_data_info = []
    
    for i, participant in enumerate(data):
        user_id = participant.get("Please enter your experiment ID. ", f"User_{i+1}")
        raw_scores = []
        valid = True
        
        for j, item in enumerate(sus_items):
            score = participant.get(item)
            if is_valid_number(score):
                raw_scores.append(int(float(score)))
            else:
                valid = False
                missing_data_info.append(f"用户 {user_id} 的 SUS 题目 {j+1} 缺失或无效: {score}")
                break
        
        # 计算SUS分数（仅当所有题目都有有效数据时）
        if valid and len(raw_scores) == 10:
            # 奇数题（1,3,5,7,9）: 得分 = 评分 - 1
            # 偶数题（2,4,6,8,10）: 得分 = 5 - 评分
            converted_scores = []
            for k, score in enumerate(raw_scores):
                if k % 2 == 0:  # 奇数题（0-indexed为偶数）
                    converted_scores.append(score - 1)
                else:  # 偶数题（0-indexed为奇数）
                    converted_scores.append(5 - score)
            
            total_score = sum(converted_scores)
            sus_score = total_score * 2.5  # 转换为0-100分制
            sus_scores.append(sus_score)
        else:
            sus_scores.append(None)
    
    # 报告缺失数据
    if missing_data_info:
        print("发现缺失或无效数据:")
        for info in missing_data_info[:5]:  # 只显示前5条
            print(f"  {info}")
        if len(missing_data_info) > 5:
            print(f"  ... 还有 {len(missing_data_info) - 5} 条缺失数据")
    
    # 过滤掉None值
    valid_sus_scores = [score for score in sus_scores if score is not None]
    
    if valid_sus_scores:
        print(f"\n有效样本数: {len(valid_sus_scores)}")
        print(f"平均分: {np.mean(valid_sus_scores):.2f}")
        print(f"标准差: {np.std(valid_sus_scores, ddof=1):.2f}")
        print(f"中位数: {np.median(valid_sus_scores):.2f}")
        print(f"最小值: {np.min(valid_sus_scores):.2f}")
        print(f"最大值: {np.max(valid_sus_scores):.2f}")
        print(f"偏度: {skew(valid_sus_scores):.2f}")
        print(f"峰度: {kurtosis(valid_sus_scores):.2f}")
        
        # 解释
        mean_score = np.mean(valid_sus_scores)
        if mean_score > 68:
            print(f"\n解释: SUS平均分 {mean_score:.2f} > 68，表示系统可用性较好")
        else:
            print(f"\n解释: SUS平均分 {mean_score:.2f} ≤ 68，表示系统可用性有待改进")
    else:
        print("没有有效的SUS数据")
    
    return sus_scores

def analyze_nasa_tlx(data):
    """分析NASA-TLX量表数据"""
    print("\n" + "=" * 50)
    print("NASA Task Load Index (NASA-TLX) 分析")
    print("=" * 50)
    
    # NASA-TLX量表题目 (6个维度)
    nasa_items = [
        "  How much mental and perceptual activity was required (e.g., thinking, deciding, calculating, remembering, looking, searching, etc.)?  ",
        "How much physical activity was required (e.g., pushing, pulling, turning, controlling, activating, etc.)? ",
        "How much time pressure did you feel due to the rate or pace at which the tasks occurred? ",
        "How successful do you think you were in accomplishing the goals of the task set by the experimenter (or yourself)? How satisfied were you with your performance in accomplishing these goals? ",
        "How hard did you have to work (mentally and physically) to accomplish your level of performance? ",
        "How insecure, discouraged, irritated, stressed, and annoyed versus secure, gratified, content, relaxed, and complacent did you feel during the task? "
    ]
    
    dimension_names = [
        "Mental Demand",
        "Physical Demand", 
        "Temporal Demand",
        "Performance",
        "Effort",
        "Frustration"
    ]
    
    # 存储各维度得分
    dimension_scores = {name: [] for name in dimension_names}
    missing_data_info = []
    
    for i, participant in enumerate(data):
        user_id = participant.get("Please enter your experiment ID. ", f"User_{i+1}")
        for j, item in enumerate(nasa_items):
            score = participant.get(item)
            if is_valid_number(score):
                dimension_scores[dimension_names[j]].append(int(float(score)))
            else:
                missing_data_info.append(f"用户 {user_id} 的 NASA-TLX 维度 {dimension_names[j]} 缺失或无效: {score}")
    
    # 报告缺失数据
    if missing_data_info:
        print("发现缺失或无效数据:")
        for info in missing_data_info[:5]:  # 只显示前5条
            print(f"  {info}")
        if len(missing_data_info) > 5:
            print(f"  ... 还有 {len(missing_data_info) - 5} 条缺失数据")
    
    # 分析各维度
    print(f"\n样本数: {len(data)}")
    print("\n各维度统计信息:")
    print("-" * 60)
    print(f"{'维度':<15} {'平均分':<8} {'标准差':<8} {'中位数':<8} {'最小值':<8} {'最大值':<8}")
    print("-" * 60)
    
    dimension_means = {}
    for name, scores in dimension_scores.items():
        if scores:
            mean = np.mean(scores)
            dimension_means[name] = mean
            print(f"{name:<15} {mean:<8.2f} {np.std(scores, ddof=1):<8.2f} {np.median(scores):<8.2f} {np.min(scores):<8.2f} {np.max(scores):<8.2f}")
        else:
            print(f"{name:<15} {'无数据':<8}")
    
    # 找出最高和最低负荷维度
    if dimension_means:
        max_dimension = max(dimension_means, key=dimension_means.get)
        min_dimension = min(dimension_means, key=dimension_means.get)
        print(f"\n最高负荷维度: {max_dimension} ({dimension_means[max_dimension]:.2f}/20)")
        print(f"最低负荷维度: {min_dimension} ({dimension_means[min_dimension]:.2f}/20)")
    
    return dimension_scores

def analyze_programming_self_efficacy(data):
    """分析改编版Computer Programming Self-Efficacy Scale数据"""
    print("\n" + "=" * 50)
    print("改编版 Computer Programming Self-Efficacy Scale 分析")
    print("=" * 50)
    
    # 四个维度的题目
    dimensions = {
        "Programming Logic & Understanding": [
            "  I can understand the basic logical structure of HTML, CSS, and JavaScript code.  ",
            "  I can understand how conditional statements (e.g., if...else) work with AI support.  ",
            "I can predict the result of a JavaScript program when given specific input values. "
        ],
        "Debugging & Problem Solving": [
            "  I can identify and correct errors in my HTML, CSS, or JavaScript code with the help of AI.  ",
            "I can understand error messages and AI-generated explanations when my code does not run correctly. ",
            "I can improve my programming skills by learning from AI debugging suggestions. "
        ],
        "Code Writing & Application": [
            "I can write a simple web page using HTML, CSS, and JavaScript with AI guidance. ",
            "I can use AI to help me apply loops, conditions, or functions in JavaScript. ",
            "I can combine AI suggestions with my own knowledge to solve a programming task. "
        ],
        "Confidence & Collaboration": [
            "I feel confident that I can complete programming exercises with AI support. ",
            "I believe I can continue learning web development effectively with AI assistance. ",
            "I can work more efficiently by dividing tasks between myself and AI (e.g., I focus on design, AI helps with debugging). "
        ]
    }
    
    # 存储各维度得分
    dimension_scores = {name: [] for name in dimensions.keys()}
    overall_scores = []
    missing_data_info = []
    
    for i, participant in enumerate(data):
        user_id = participant.get("Please enter your experiment ID. ", f"User_{i+1}")
        participant_dimension_scores = {}
        
        # 计算各维度得分
        for dim_name, items in dimensions.items():
            dim_scores = []
            for j, item in enumerate(items):
                score = participant.get(item)
                if is_valid_number(score):
                    dim_scores.append(float(score))
                else:
                    missing_data_info.append(f"用户 {user_id} 的 CPS 维度 {dim_name} 题目 {j+1} 缺失或无效: {score}")
            
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
    
    # 报告缺失数据
    if missing_data_info:
        print("发现缺失或无效数据:")
        for info in missing_data_info:
            print(f"  {info}")
    
    # 分析各维度
    valid_overall_count = len([s for s in overall_scores if s is not None])
    print(f"\n有效样本数: {valid_overall_count}")
    print("\n各维度统计信息:")
    print("-" * 70)
    print(f"{'维度':<30} {'平均分':<8} {'标准差':<8} {'中位数':<8} {'最小值':<8} {'最大值':<8}")
    print("-" * 70)
    
    dimension_means = {}
    for name, scores in dimension_scores.items():
        valid_scores = [s for s in scores if s is not None]
        if valid_scores:
            mean = np.mean(valid_scores)
            dimension_means[name] = mean
            print(f"{name:<30} {mean:<8.2f} {np.std(valid_scores, ddof=1):<8.2f} {np.median(valid_scores):<8.2f} {np.min(valid_scores):<8.2f} {np.max(valid_scores):<8.2f}")
        else:
            print(f"{name:<30} {'无数据':<8}")
    
    # 总体统计
    valid_overall_scores = [s for s in overall_scores if s is not None]
    if valid_overall_scores:
        print("\n总体自我效能统计:")
        print("-" * 40)
        print(f"平均分: {np.mean(valid_overall_scores):.2f}")
        print(f"标准差: {np.std(valid_overall_scores, ddof=1):.2f}")
        print(f"中位数: {np.median(valid_overall_scores):.2f}")
        print(f"最小值: {np.min(valid_overall_scores):.2f}")
        print(f"最大值: {np.max(valid_overall_scores):.2f}")
        
        # 找出最高和最低维度
        if dimension_means:
            max_dimension = max(dimension_means, key=dimension_means.get)
            min_dimension = min(dimension_means, key=dimension_means.get)
            print(f"\n最高自我效能维度: {max_dimension} ({dimension_means[max_dimension]:.2f}/5)")
            print(f"最低自我效能维度: {min_dimension} ({dimension_means[min_dimension]:.2f}/5)")
            
            # 解释总体得分
            overall_mean = np.mean(valid_overall_scores)
            if overall_mean >= 4:
                print(f"\n解释: 总体编程自我效能感较高 (M={overall_mean:.2f}/5)")
            elif overall_mean >= 3:
                print(f"\n解释: 总体编程自我效能感中等 (M={overall_mean:.2f}/5)")
            else:
                print(f"\n解释: 总体编程自我效能感较低 (M={overall_mean:.2f}/5)")
    
    return dimension_scores, overall_scores

def calculate_cronbach_alpha(data, items):
    """计算Cronbach's α信度系数"""
    # 提取数据
    scores_matrix = []
    
    for item in items:
        item_scores = []
        for participant in data:
            score = participant.get(item)
            if is_valid_number(score):
                item_scores.append(float(score))
            else:
                item_scores.append(np.nan)
        
        scores_matrix.append(item_scores)
    
    if len(scores_matrix) < 2:
        return None
    
    # 转换为numpy数组
    scores_array = np.array(scores_matrix).T
    
    # 移除包含NaN的行
    valid_rows = ~np.isnan(scores_array).any(axis=1)
    if not np.any(valid_rows):
        return None
    
    scores_array = scores_array[valid_rows]
    
    if scores_array.shape[0] < 2:  # 至少需要2个样本
        return None
    
    # 计算Cronbach's α
    k = scores_array.shape[1]  # 题目数
    if k < 2:
        return None
    
    # 计算总方差
    total_var = np.var(scores_array.sum(axis=1), ddof=1)
    
    # 计算各题目方差和
    item_var_sum = np.sum(np.var(scores_array, axis=0, ddof=1))
    
    # 计算Cronbach's α
    if total_var > 0 and (k - 1) > 0:
        alpha = (k / (k - 1)) * (1 - (item_var_sum / total_var))
        return max(0, alpha)  # 确保α不为负数
    else:
        return None

def analyze_reliability(data):
    """分析各量表的信度"""
    print("\n" + "=" * 50)
    print("量表信度分析 (Cronbach's α)")
    print("=" * 50)
    
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
    
    alpha = calculate_cronbach_alpha(data, sus_items)
    if alpha is not None:
        print(f"SUS量表 Cronbach's α: {alpha:.3f}")
        if alpha >= 0.9:
            print("  信度非常好")
        elif alpha >= 0.8:
            print("  信度良好")
        elif alpha >= 0.7:
            print("  信度可以接受")
        else:
            print("  信度较低，需要改进")
    else:
        print("SUS量表: 无法计算Cronbach's α")
    
    # NASA-TLX量表题目
    nasa_items = [
        "  How much mental and perceptual activity was required (e.g., thinking, deciding, calculating, remembering, looking, searching, etc.)?  ",
        "How much physical activity was required (e.g., pushing, pulling, turning, controlling, activating, etc.)? ",
        "How much time pressure did you feel due to the rate or pace at which the tasks occurred? ",
        "How successful do you think you were in accomplishing the goals of the task set by the experimenter (or yourself)? How satisfied were you with your performance in accomplishing these goals? ",
        "How hard did you have to work (mentally and physically) to accomplish your level of performance? ",
        "How insecure, discouraged, irritated, stressed, and annoyed versus secure, gratified, content, relaxed, and complacent did you feel during the task? "
    ]
    
    alpha = calculate_cronbach_alpha(data, nasa_items)
    if alpha is not None:
        print(f"NASA-TLX量表 Cronbach's α: {alpha:.3f}")
        if alpha >= 0.9:
            print("  信度非常好")
        elif alpha >= 0.8:
            print("  信度良好")
        elif alpha >= 0.7:
            print("  信度可以接受")
        else:
            print("  信度较低，需要改进")
    else:
        print("NASA-TLX量表: 无法计算Cronbach's α")
    
    # 编程自我效能感量表题目
    cpses_items = [
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
    
    alpha = calculate_cronbach_alpha(data, cpses_items)
    if alpha is not None:
        print(f"编程自我效能感量表 Cronbach's α: {alpha:.3f}")
        if alpha >= 0.9:
            print("  信度非常好")
        elif alpha >= 0.8:
            print("  信度良好")
        elif alpha >= 0.7:
            print("  信度可以接受")
        else:
            print("  信度较低，需要改进")
    else:
        print("编程自我效能感量表: 无法计算Cronbach's α")

def generate_summary_report(sus_scores, nasa_scores, cpses_dimension_scores, cpses_overall_scores):
    """生成总结报告"""
    print("\n" + "=" * 60)
    print("总结报告")
    print("=" * 60)
    
    # SUS结果总结
    valid_sus_scores = [s for s in sus_scores if s is not None]
    if valid_sus_scores:
        sus_mean = np.mean(valid_sus_scores)
        print(f"1. 系统可用性 (SUS):")
        print(f"   - 平均得分: {sus_mean:.2f}/100")
        if sus_mean > 68:
            print(f"   - 结论: 系统可用性较好 (高于平均水平)")
        else:
            print(f"   - 结论: 系统可用性有待改进 (低于平均水平)")
    
    # NASA-TLX结果总结
    print(f"\n2. 任务负荷 (NASA-TLX):")
    dimension_means = {}
    for name, scores in nasa_scores.items():
        valid_scores = [s for s in scores if s is not None]
        if valid_scores:
            dimension_means[name] = np.mean(valid_scores)
    
    if dimension_means:
        max_dim = max(dimension_means, key=dimension_means.get)
        min_dim = min(dimension_means, key=dimension_means.get)
        print(f"   - 最高负荷维度: {max_dim} ({dimension_means[max_dim]:.2f}/20)")
        print(f"   - 最低负荷维度: {min_dim} ({dimension_means[min_dim]:.2f}/20)")
        mental_workload = dimension_means.get("Mental Demand", 0)
        frustration = dimension_means.get("Frustration", 0)
        print(f"   - 认知负荷: {mental_workload:.2f}/20")
        print(f"   - 挫败感: {frustration:.2f}/20")
        
        # 解释任务负荷
        if mental_workload > 10:
            print(f"   - 解释: 认知负荷较高，学习者需要较多 mental effort")
        else:
            print(f"   - 解释: 认知负荷适中，学习者mental effort负担合理")
            
        if frustration < 5:
            print(f"   - 解释: 挫败感较低，学习体验较好")
        else:
            print(f"   - 解释: 挫败感较高，可能需要改进用户体验")
    
    # 编程自我效能感结果总结
    valid_overall_scores = [s for s in cpses_overall_scores if s is not None]
    if valid_overall_scores:
        cpses_mean = np.mean(valid_overall_scores)
        print(f"\n3. 编程自我效能感:")
        print(f"   - 平均得分: {cpses_mean:.2f}/5")
        if cpses_mean >= 4:
            print(f"   - 结论: 学习者具有较高的编程自我效能感")
        elif cpses_mean >= 3:
            print(f"   - 结论: 学习者具有中等的编程自我效能感")
        else:
            print(f"   - 结论: 学习者编程自我效能感较低")
        
        # 分析各维度
        dimension_means = {}
        for name, scores in cpses_dimension_scores.items():
            valid_scores = [s for s in scores if s is not None]
            if valid_scores:
                dimension_means[name] = np.mean(valid_scores)
        
        if dimension_means:
            # 找出最高和最低维度
            max_dim = max(dimension_means, key=dimension_means.get)
            min_dim = min(dimension_means, key=dimension_means.get)
            print(f"   - 最高维度: {max_dim} ({dimension_means[max_dim]:.2f}/5)")
            print(f"   - 最低维度: {min_dim} ({dimension_means[min_dim]:.2f}/5)")
            
            # 解释各维度表现
            if dimension_means.get("Confidence & Collaboration", 0) >= 4:
                print(f"   - 解释: 学习者在协作与信心方面表现良好")
            if dimension_means.get("Debugging & Problem Solving", 0) >= 4:
                print(f"   - 解释: 学习者在调试与问题解决方面表现良好")
            if dimension_means.get("Programming Logic & Understanding", 0) >= 4:
                print(f"   - 解释: 学习者在编程逻辑与理解方面表现良好")

def main():
    """主函数"""
    # 加载数据
    data = load_data()
    print(f"总共 {len(data)} 份问卷数据")
    
    # 分析SUS量表
    sus_scores = analyze_sus(data)
    
    # 分析NASA-TLX量表
    nasa_scores = analyze_nasa_tlx(data)
    
    # 分析编程自我效能感量表
    cpses_dimension_scores, cpses_overall_scores = analyze_programming_self_efficacy(data)
    
    # 分析信度
    analyze_reliability(data)
    
    # 生成总结报告
    generate_summary_report(sus_scores, nasa_scores, cpses_dimension_scores, cpses_overall_scores)
    
    print("\n" + "=" * 50)
    print("分析完成")
    print("=" * 50)

if __name__ == "__main__":
    main()
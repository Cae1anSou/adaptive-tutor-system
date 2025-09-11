import pandas as pd
import json

def analyze_and_convert_csv():
    # 使用GBK编码读取CSV文件
    csv_file_path = 'Data_Analyze/questionnaire/Untitled form.csv'
    df = pd.read_csv(csv_file_path, encoding='gbk')
    
    print("数据基本信息:")
    print(f"数据形状: {df.shape}")
    print(f"列数: {len(df.columns)}")
    print(f"行数: {len(df)}")
    
    # 显示所有列名
    print("\n所有列名:")
    for i, col in enumerate(df.columns):
        print(f"{i+1:2d}. {col}")
    
    # 转换为JSON格式
    data_json = df.to_dict(orient='records')
    
    # 保存为JSON文件
    json_file_path = 'Data_Analyze/questionnaire/survey_data.json'
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(data_json, f, ensure_ascii=False, indent=2)
    
    print(f"\n数据已保存为JSON格式到 {json_file_path}!")
    
    # 基本统计信息
    print("\n数值列的统计信息:")
    numeric_columns = df.select_dtypes(include=['number']).columns
    if len(numeric_columns) > 0:
        print(df[numeric_columns].describe())
    else:
        print("没有找到数值列")
    
    # 检查缺失值
    print("\n缺失值统计 (前10列):")
    print(df.isnull().sum()[:10])
    
    # 显示前几行数据作为示例
    print("\n前3行数据示例:")
    print(df.head(3))

if __name__ == '__main__':
    analyze_and_convert_csv()
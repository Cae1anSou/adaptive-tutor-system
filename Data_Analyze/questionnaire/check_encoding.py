# 检查文件编码和内容
import chardet

# 检测文件编码
with open('Data_Analyze/questionnaire/Untitled form.csv', 'rb') as f:
    raw_data = f.read()
    encoding = chardet.detect(raw_data)['encoding']
    print(f"文件编码: {encoding}")

# 读取并显示部分原始内容
with open('Data_Analyze/questionnaire/Untitled form.csv', 'r', encoding=encoding) as f:
    lines = f.readlines()
    
# 查找baseline007的行
for i, line in enumerate(lines):
    if 'baseline007' in line:
        print(f"\n第{i+1}行 (baseline007):")
        print(repr(line))  # 显示原始字符串表示
        print("\n分割后的字段:")
        fields = line.strip().split(',')
        for j, field in enumerate(fields):
            print(f"  字段{j}: {repr(field)}")
        break
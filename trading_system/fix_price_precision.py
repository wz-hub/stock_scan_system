"""
修复价格精度问题 - 补丁
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# 读取文件
with open('signal_generator.py', 'r') as f:
    content = f.read()

# 修复 1: 所有价格相关字段都转为字符串保留完整精度
replacements = [
    ("current_price = row['close']", "current_price = str(row['close'])  # 保留完整精度"),
    ("entry_price=current_price,", "entry_price=str(current_price),"),
    ("stop_loss_price=round(stop_loss, 2),", "stop_loss_price=str(stop_loss),"),
    ("take_profit_price=round(take_profit, 2),", "take_profit_price=str(take_profit),"),
]

for old, new in replacements:
    content = content.replace(old, new)

# 写入文件
with open('signal_generator.py', 'w') as f:
    f.write(content)

print("✅ 价格精度修复完成！")
print("   所有价格字段现在都保留完整精度（字符串格式）")

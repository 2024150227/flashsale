import os
import fnmatch

def search_all_files(root_dir, search_text):
    matches = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if fnmatch.fnmatch(filename, '*.py') or fnmatch.fnmatch(filename, '*.pyc'):
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if search_text in content:
                            matches.append(filepath)
                except:
                    pass
    return matches

# 搜索错误消息
error_msg = "您已购买过该商品"
print(f"搜索消息: {error_msg}")
print("=" * 50)

matches = search_all_files('e:\\Desktop\\高并发秒杀系统', error_msg)
if matches:
    print("找到以下文件包含该消息:")
    for match in matches:
        print(f"  - {match}")
else:
    print("未找到包含该消息的文件")
    print("\n可能的原因:")
    print("1. 消息可能存储在数据库中")
    print("2. 消息可能在运行时动态生成")
    print("3. 服务可能运行在容器中，使用的是不同的代码")
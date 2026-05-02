import subprocess
import os
#脚本管理MySQL数据库，包括创建、查看、描述表结构、执行SQL语句等
def run_command(cmd):
    """执行命令并返回输出"""
    print(f"\n📝 执行命令: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print("✅ 输出:")
        print(result.stdout)
    if result.stderr:
        print("❌ 错误:")
        print(result.stderr)
    return result.returncode == 0

def enter_container(container_name="flashsale-mysql"):
    """进入容器"""
    print(f"\n🚪 进入容器: {container_name}")
    cmd = f"docker exec -it {container_name} bash"
    # 交互式命令需要特殊处理
    subprocess.run(cmd, shell=True)

#权重：1（低频率，但最重要）
def create_database(db_name, container_name="flashsale-mysql"):
    """创建新数据库"""
    print(f"\n🗄️ 创建数据库: {db_name}")
    cmd = f'''docker exec {container_name} mysql -u root --password=mysql123456 -e "CREATE DATABASE IF NOT EXISTS {db_name};"'''
    return run_command(cmd)

#权重：1（低频率，但最重要）
def show_databases(container_name="flashsale-mysql"):
    """查看所有数据库"""
    print("\n📊 查看所有数据库")
    cmd = f'''docker exec {container_name} mysql -u root --password=mysql123456 -e "SHOW DATABASES;"'''
    return run_command(cmd)

#权重：1（低频率，但最重要）
def show_tables(db_name, container_name="flashsale-mysql"):
    """查看数据库中的表"""
    print(f"\n📋 查看数据库 {db_name} 中的表")
    cmd = f'''docker exec {container_name} mysql -u root --password=mysql123456 -D {db_name} -e "SHOW TABLES;"'''
    return run_command(cmd)

#权重：1（低频率，但最重要）
def describe_table(db_name, table_name, container_name="flashsale-mysql"):
    """查看表结构"""
    print(f"\n🔍 查看表 {db_name}.{table_name} 的结构")
    cmd = f'''docker exec {container_name} mysql -u root --password=mysql123456 -D {db_name} -e "DESCRIBE {table_name};"'''
    return run_command(cmd)

#权重：1（低频率，但最重要）
def execute_sql(sql, container_name="flashsale-mysql"):
    """执行任意 SQL 语句"""
    print(f"\n⚙️ 执行 SQL: {sql[:50]}...")
    cmd = f'''docker exec {container_name} mysql -u root --password=mysql123456 -e "{sql}"'''
    return run_command(cmd)

def pause():
    """暂停并等待用户按 Enter 键"""
    input("\n按 Enter 键继续...")

def main():
    print("=====================================")
    print("      MySQL 容器管理脚本")
    print("=====================================")
    
    while True:
        print("\n请选择操作:")
        print("1. 查看所有数据库")
        print("2. 创建新数据库")
        print("3. 查看数据库中的表")
        print("4. 查看表结构")
        print("5. 进入容器交互模式")
        print("6. 执行自定义 SQL")
        print("0. 退出")
        
        choice = input("\n输入选项: ")
        
        if choice == "1":
            show_databases()
            pause()
        elif choice == "2":
            db_name = input("输入数据库名称: ")
            create_database(db_name)
            pause()
        elif choice == "3":
            db_name = input("输入数据库名称: ")
            show_tables(db_name)
            pause()
        elif choice == "4":
            db_name = input("输入数据库名称: ")
            table_name = input("输入表名称: ")
            describe_table(db_name, table_name)
            pause()
        elif choice == "5":
            enter_container()
            pause()
        elif choice == "6":
            sql = input("输入 SQL 语句: ")
            execute_sql(sql)
            pause()
        elif choice == "0":
            print("👋 退出脚本")
            break
        else:
            print("❌ 无效选项")
            pause()

if __name__ == "__main__":
    main()
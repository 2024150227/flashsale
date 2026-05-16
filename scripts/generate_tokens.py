"""
批量生成测试用户和Token脚本
"""
import requests
import json

BASE_URL = "http://localhost:8000"
USER_COUNT = 50  # 生成50个测试用户

def generate_tokens():
    tokens = []
    
    for i in range(USER_COUNT):
        username = f"flashsale_user_{i:04d}"
        password = "test123456"
        
        try:
            # 先尝试登录（用户可能已存在）
            login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
                "username": username,
                "password": password
            })
            
            if login_response.status_code == 200:
                data = login_response.json()
                token = data.get("access_token")
                tokens.append(token)
                print(f"登录成功 {i+1}/{USER_COUNT}: {username}")
            else:
                # 登录失败，尝试注册
                register_response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
                    "username": username,
                    "password": password,
                    "name": f"User_{i}",
                    "age": 25
                })
                
                if register_response.status_code in [200, 201]:
                    # 注册成功后登录
                    login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
                        "username": username,
                        "password": password
                    })
                    
                    if login_response.status_code == 200:
                        data = login_response.json()
                        token = data.get("access_token")
                        tokens.append(token)
                        print(f"注册并登录 {i+1}/{USER_COUNT}: {username}")
                    else:
                        print(f"注册成功但登录失败: {username}")
                else:
                    print(f"注册失败: {username}")
        except Exception as e:
            print(f"处理用户失败: {username}, {e}")
    
    # 保存到文件
    with open("scripts/tokens.json", "w") as f:
        json.dump(tokens, f)
    
    print(f"\n成功生成 {len(tokens)} 个Token，已保存到 scripts/tokens.json")
    return tokens

if __name__ == "__main__":
    generate_tokens()

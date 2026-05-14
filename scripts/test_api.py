"""
API诊断脚本 - 测试各个接口是否正常
"""
import requests
import time

BASE_URL = "http://localhost:8000"

def test_api():
    print("=== API诊断测试 ===\n")

    # 1. 测试根路径
    print("1. 测试根路径 /")
    try:
        r = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"   状态码: {r.status_code}")
    except Exception as e:
        print(f"   错误: {e}")

    # 2. 测试docs
    print("\n2. 测试API文档 /docs")
    try:
        r = requests.get(f"{BASE_URL}/docs", timeout=5)
        print(f"   状态码: {r.status_code}")
    except Exception as e:
        print(f"   错误: {e}")

    # 3. 测试注册
    print("\n3. 测试用户注册 /api/v1/auth/register")
    try:
        r = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "username": f"test_{int(time.time())}",
            "password": "test123456",
            "name": "Test User",
            "age": 25
        }, timeout=10)
        print(f"   状态码: {r.status_code}")
        print(f"   响应: {r.text[:200]}")
    except Exception as e:
        print(f"   错误: {e}")

    # 4. 测试登录
    print("\n4. 测试用户登录 /api/v1/auth/login")
    try:
        r = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
            "username": "test_user",
            "password": "test123456"
        }, timeout=10)
        print(f"   状态码: {r.status_code}")
        print(f"   响应: {r.text[:200]}")
    except Exception as e:
        print(f"   错误: {e}")

    # 5. 测试商品列表
    print("\n5. 测试商品列表 /api/v1/products/")
    try:
        r = requests.get(f"{BASE_URL}/api/v1/products/", timeout=10)
        print(f"   状态码: {r.status_code}")
        print(f"   响应: {r.text[:200]}")
    except Exception as e:
        print(f"   错误: {e}")

    print("\n=== 诊断完成 ===")

if __name__ == "__main__":
    test_api()

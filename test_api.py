import requests
import json

BASE_URL = "http://localhost:8000"

def test_health_check():
    """测试健康检查API"""
    print("测试健康检查API...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()
    return response.status_code == 200

def test_root():
    """测试根路径"""
    print("测试根路径...")
    response = requests.get(f"{BASE_URL}/")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()
    return response.status_code == 200

def test_register():
    """测试用户注册"""
    print("测试用户注册...")
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    }
    response = requests.post(f"{BASE_URL}/api/auth/register", json=user_data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()
    return response.status_code == 200

def test_login():
    """测试用户登录"""
    print("测试用户登录...")
    login_data = {
        "username": "testuser",
        "password": "password123"
    }
    response = requests.post(f"{BASE_URL}/api/auth/token", data=login_data)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"响应: {{'access_token': '...', 'token_type': '{data['token_type']}', 'user': {...}}}")
        return data.get("access_token")
    else:
        print(f"响应: {response.json()}")
    print()
    return None

if __name__ == "__main__":
    print("开始测试 Hybrid LLM Gateway API...")
    print("=" * 50)
    
    # 运行测试
    tests = [
        test_health_check,
        test_root,
        test_register,
        test_login
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print("=" * 50)
    print("测试结果汇总:")
    print(f"通过: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 所有测试通过！API服务正常运行。")
    else:
        print("❌ 部分测试失败，请检查服务配置。")

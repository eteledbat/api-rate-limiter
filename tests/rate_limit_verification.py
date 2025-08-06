# rate_limit_verification.py
import asyncio
import aiohttp

async def test_rate_limits():
    """专门测试速率限制功能"""
    
    # 使用严格限制的key
    headers = {"Authorization": "Bearer test-key-1"}  # 假设这个key有较低限制
    
    async with aiohttp.ClientSession() as session:
        success_count = 0
        rate_limited_count = 0
        
        print("🔬 测试速率限制功能...")
        
        # 快速发送请求直到触发限制
        for i in range(500):
            try:
                async with session.post(
                    "http://127.0.0.1:8003/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": "gpt-4-turbo",
                        "messages": [{"role": "user", "content": f"Test {i}"}]
                    }
                ) as response:
                    if response.status == 200:
                        success_count += 1
                    elif response.status == 429:
                        rate_limited_count += 1
                        print(f"✅ 速率限制在第 {i+1} 个请求时触发")
                        break
            except Exception as e:
                print(f"请求失败: {e}")
        
        print(f"成功请求: {success_count}")
        print(f"被限制请求: {rate_limited_count}")
        
        return rate_limited_count > 0

if __name__ == "__main__":
    result = asyncio.run(test_rate_limits())
    if result:
        print("✅ 速率限制功能正常")
    else:
        print("❌ 速率限制未触发，请检查配置")
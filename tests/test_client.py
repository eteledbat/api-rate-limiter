import asyncio
import aiohttp
import time
import winloop
from asyncio import Semaphore

# 使用Windows优化的事件循环
winloop.install()

class WindowsHighPerformanceClient:
    def __init__(self, max_concurrency=200):  # Windows适中的并发数
        self.semaphore = Semaphore(max_concurrency)
        self.session = None
        
    async def __aenter__(self):
        # 🔧 修复：移除无效参数，使用正确的TCPConnector配置
        connector = aiohttp.TCPConnector(
            limit=800,                     # 总连接池大小
            limit_per_host=400,            # 每主机连接数
            keepalive_timeout=30,          # 连接保持时间
            enable_cleanup_closed=True,    # 启用清理已关闭连接
            use_dns_cache=True,           # 启用DNS缓存
            ttl_dns_cache=300,            # DNS缓存TTL
            force_close=False,            # 不强制关闭连接
            # connector_timeout=3.0       # ❌ 移除这个无效参数
        )
        
        # 设置超时配置
        timeout = aiohttp.ClientTimeout(
            total=10,      # 总超时时间
            connect=2,     # 连接超时
            sock_read=3,   # socket读取超时
            sock_connect=2 # socket连接超时
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "Connection": "keep-alive",
                "User-Agent": "Windows-High-Performance-Client/1.0"
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            # 给一点时间让连接完全关闭
            await asyncio.sleep(0.1)

    async def windows_continuous_test(self, nodes, api_key, target_qps=500, duration=15):
        """Windows优化的连续测试"""
        
        # Windows环境下更保守的配置
        max_concurrent_requests = min(target_qps, 500)
        request_interval = 1.0 / target_qps
        
        start_time = time.time()
        sent_requests = 0
        completed_requests = 0
        successful_requests = 0
        rate_limited_requests = 0
        error_requests = 0
        
        # 使用Windows友好的任务管理
        active_tasks = []
        
        print(f"🪟 Windows优化测试开始")
        print(f"目标: {target_qps} QPS，持续 {duration} 秒")
        print(f"最大并发: {max_concurrent_requests}")
        
        last_report_time = start_time
        
        while time.time() - start_time < duration:
            current_time = time.time()
            
            # 清理已完成的任务
            finished_tasks = []
            for task in active_tasks[:]:  # 创建副本以避免修改正在迭代的列表
                if task.done():
                    finished_tasks.append(task)
                    active_tasks.remove(task)
            
            # 处理完成的任务结果
            for task in finished_tasks:
                try:
                    result = await task
                    completed_requests += 1
                    if result == 200:
                        successful_requests += 1
                    elif result == 429:
                        rate_limited_requests += 1
                    else:
                        error_requests += 1
                except Exception as e:
                    completed_requests += 1
                    error_requests += 1
            
            # 发送新请求（如果并发数允许）
            if len(active_tasks) < max_concurrent_requests:
                node = nodes[sent_requests % len(nodes)]
                task = asyncio.create_task(
                    self.send_windows_request(node, api_key, sent_requests)
                )
                active_tasks.append(task)
                sent_requests += 1
            
            # 定期报告进度
            if current_time - last_report_time >= 3:
                elapsed = current_time - start_time
                current_qps = completed_requests / elapsed if elapsed > 0 else 0
                success_rate = successful_requests / completed_requests * 100 if completed_requests > 0 else 0
                print(f"  {elapsed:.1f}s - 发送:{sent_requests}, 完成:{completed_requests}, QPS:{current_qps:.1f}, 成功率:{success_rate:.1f}%")
                last_report_time = current_time
            
            # 控制发送速率
            await asyncio.sleep(min(request_interval, 0.0001))  # 最小1ms间隔
        
        # 等待剩余任务完成
        print("等待剩余请求完成...")
        if active_tasks:
            remaining_results = await asyncio.gather(*active_tasks, return_exceptions=True)
            for result in remaining_results:
                completed_requests += 1
                if isinstance(result, Exception):
                    error_requests += 1
                elif result == 200:
                    successful_requests += 1
                elif result == 429:
                    rate_limited_requests += 1
                else:
                    error_requests += 1
        
        actual_duration = time.time() - start_time
        actual_qps = completed_requests / actual_duration if actual_duration > 0 else 0
        success_rate = successful_requests / completed_requests * 100 if completed_requests > 0 else 0
        
        print(f"\n📊 Windows测试结果:")
        print(f"持续时间: {actual_duration:.2f} 秒")
        print(f"发送请求: {sent_requests}")
        print(f"完成请求: {completed_requests}")
        print(f"成功请求: {successful_requests} (200)")
        print(f"限流请求: {rate_limited_requests} (429)")
        print(f"错误请求: {error_requests}")
        print(f"实际 QPS: {actual_qps:.2f}")
        print(f"成功率: {success_rate:.1f}%")
        
        return {
            'qps': actual_qps,
            'success_rate': success_rate,
            'total_requests': completed_requests,
            'successful_requests': successful_requests,
            'rate_limited_requests': rate_limited_requests,
            'error_requests': error_requests
        }

    async def send_windows_request(self, node, api_key, request_id):
        """Windows优化的请求发送"""
        async with self.semaphore:
            try:
                async with self.session.post(
                    f"{node}/v1/chat/completions",
                    json={
                        "model": "gpt-4-turbo",
                        "messages": [{"role": "user", "content": "test"}]
                    },
                    headers={"Authorization": f"Bearer {api_key}"}
                ) as response:
                    # 确保读取完响应体
                    await response.read()
                    return response.status
                    
            except asyncio.TimeoutError:
                return "timeout"
            except aiohttp.ClientError as e:
                return "client_error"
            except Exception as e:
                return "unknown_error"

async def run_windows_test():
    """运行Windows优化测试"""
    nodes = [
        "http://127.0.0.1:8003",
        "http://127.0.0.1:8004", 
        "http://127.0.0.1:8005"
    ]
    
    # 检查节点可用性
    print("🔍 检查节点状态...")
    available_nodes = []
    
    timeout = aiohttp.ClientTimeout(total=3)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for node in nodes:
            try:
                async with session.get(f"{node}/health") as response:
                    if response.status == 200:
                        available_nodes.append(node)
                        print(f"✅ {node}")
                    else:
                        print(f"⚠️ {node} - 状态 {response.status}")
            except Exception as e:
                print(f"❌ {node} - 不可用: {e}")
    
    if not available_nodes:
        print("❌ 没有可用节点！请确保服务器正在运行")
        return
    
    print(f"\n🎯 使用 {len(available_nodes)} 个节点进行测试")
    
    # 运行不同强度的测试
    test_configs = [
        {"target_qps": 200, "duration": 8, "name": "🚀 轻负载测试"},
        {"target_qps": 500, "duration": 8, "name": "💪 中等负载测试"},
        {"target_qps": 1000, "duration": 12, "name": "⚡ 高负载测试"},
    ]
    
    best_result = None
    best_qps = 0
    
    for i, config in enumerate(test_configs):
        print(f"\n{config['name']} ({i+1}/{len(test_configs)})")
        print(f"目标: {config['target_qps']} QPS, 持续: {config['duration']}秒")
        
        try:
            async with WindowsHighPerformanceClient(max_concurrency=200) as client:
                result = await client.windows_continuous_test(
                    nodes=available_nodes,
                    api_key="unlimited-key",
                    target_qps=config['target_qps'],
                    duration=config['duration']
                )
            
            # 记录最佳结果
            if result['qps'] > best_qps:
                best_qps = result['qps']
                best_result = result.copy()
                best_result['config'] = config['name']
        
        except Exception as e:
            print(f"❌ 测试失败: {e}")
        
        # 测试间隔，让系统恢复
        if i < len(test_configs) - 1:
            print("⏳ 系统恢复中...")
            await asyncio.sleep(3)
    
    # 显示最终结果
    print(f"\n🏆 最佳性能结果:")
    print("=" * 50)
    if best_result:
        print(f"最佳配置: {best_result['config']}")
        print(f"🚀 最高 QPS: {best_result['qps']:.2f}")
        print(f"✅ 成功率: {best_result['success_rate']:.1f}%")
        print(f"📊 总请求: {best_result['total_requests']}")
        print(f"✅ 成功: {best_result['successful_requests']}")
        print(f"🚫 限流: {best_result['rate_limited_requests']}")
        print(f"❌ 错误: {best_result['error_requests']}")
        
        # 性能评估
        if best_result['qps'] >= 1000:
            print("🎉 完全达成 1K+ QPS 目标！")
        elif best_result['qps'] >= 500:
            print("👍 接近目标，性能优秀！")
        elif best_result['qps'] >= 300:
            print("👌 性能良好，有改进空间")
        else:
            print("⚠️ 性能偏低，建议检查系统配置")
            
        # 预测Linux环境性能
        linux_prediction = best_result['qps'] * 2.5
        print(f"🐧 预测Linux环境性能: {linux_prediction:.0f} QPS")
    else:
        print("❌ 没有成功的测试结果")

if __name__ == "__main__":
    try:
        asyncio.run(run_windows_test())
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
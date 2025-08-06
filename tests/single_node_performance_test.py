import asyncio
import aiohttp
import time
import winloop
from asyncio import Semaphore
import json

# 使用Windows优化的事件循环
winloop.install()

class SingleNodePerformanceClient:
    def __init__(self, max_concurrency=500):
        self.semaphore = Semaphore(max_concurrency)
        self.session = None
        
    async def __aenter__(self):
        # 为单节点优化的连接配置
        connector = aiohttp.TCPConnector(
            limit=600,                    # 单节点更多连接
            limit_per_host=600,           # 全部用于单个节点
            keepalive_timeout=60,         # 长连接复用
            enable_cleanup_closed=True,
            use_dns_cache=True,
            ttl_dns_cache=600,
            force_close=False,
        )
        
        timeout = aiohttp.ClientTimeout(
            total=8,       # 单节点可以稍微宽松
            connect=2,
            sock_read=3,
            sock_connect=2
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "Connection": "keep-alive",
                "User-Agent": "Single-Node-Performance-Client/1.0"
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            await asyncio.sleep(0.1)

    async def single_node_stress_test(self, node_url, api_key, test_configs):
        """单节点压力测试"""
        
        print(f"🎯 单节点性能测试")
        print(f"目标节点: {node_url}")
        print(f"API Key: {api_key}")
        print("=" * 60)
        
        results = []
        
        for config in test_configs:
            print(f"\n🧪 {config['name']}")
            print(f"目标 QPS: {config['target_qps']}, 持续: {config['duration']}秒")
            
            result = await self.run_single_test(
                node_url, 
                api_key, 
                config['target_qps'], 
                config['duration']
            )
            
            results.append({
                'config': config,
                'result': result
            })
            
            # 系统恢复时间
            if config != test_configs[-1]:
                print("⏳ 系统恢复中...")
                await asyncio.sleep(5)
        
        return results

    async def run_single_test(self, node_url, api_key, target_qps, duration):
        """运行单次性能测试"""
        
        max_concurrent = min(target_qps, 500)
        request_interval = 1.0 / target_qps
        
        start_time = time.time()
        sent_requests = 0
        completed_requests = 0
        successful_requests = 0
        rate_limited_requests = 0
        error_requests = 0
        
        active_tasks = []
        response_times = []
        
        print(f"开始测试: 目标 {target_qps} QPS, 最大并发 {max_concurrent}")
        
        last_report_time = start_time
        
        while time.time() - start_time < duration:
            current_time = time.time()
            
            # 处理完成的任务
            finished_tasks = []
            for task in active_tasks[:]:
                if task.done():
                    finished_tasks.append(task)
                    active_tasks.remove(task)
            
            for task in finished_tasks:
                try:
                    result = await task
                    completed_requests += 1
                    
                    if isinstance(result, dict):
                        status = result.get('status')
                        response_time = result.get('response_time', 0)
                        response_times.append(response_time)
                        
                        if status == 200:
                            successful_requests += 1
                        elif status == 429:
                            rate_limited_requests += 1
                        else:
                            error_requests += 1
                    else:
                        error_requests += 1
                        
                except Exception:
                    error_requests += 1
                    completed_requests += 1
            
            # 发送新请求
            if len(active_tasks) < max_concurrent:
                task = asyncio.create_task(
                    self.send_single_request(node_url, api_key, sent_requests)
                )
                active_tasks.append(task)
                sent_requests += 1
            
            # 实时报告
            if current_time - last_report_time >= 3:
                elapsed = current_time - start_time
                current_qps = completed_requests / elapsed if elapsed > 0 else 0
                success_rate = successful_requests / completed_requests * 100 if completed_requests > 0 else 0
                avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                
                print(f"  {elapsed:.1f}s - 发送:{sent_requests}, 完成:{completed_requests}, QPS:{current_qps:.1f}, 成功率:{success_rate:.1f}%, 平均响应:{avg_response_time*1000:.1f}ms")
                last_report_time = current_time
            
            # 控制发送速率
            await asyncio.sleep(max(request_interval, 0.0001))
        
        # 等待剩余任务完成
        print("等待剩余请求完成...")
        if active_tasks:
            remaining_results = await asyncio.gather(*active_tasks, return_exceptions=True)
            for result in remaining_results:
                completed_requests += 1
                if isinstance(result, dict) and result.get('status') == 200:
                    successful_requests += 1
                    if 'response_time' in result:
                        response_times.append(result['response_time'])
                elif isinstance(result, dict) and result.get('status') == 429:
                    rate_limited_requests += 1
                else:
                    error_requests += 1
        
        # 计算最终结果
        actual_duration = time.time() - start_time
        actual_qps = completed_requests / actual_duration if actual_duration > 0 else 0
        success_rate = successful_requests / completed_requests * 100 if completed_requests > 0 else 0
        
        # 响应时间统计
        if response_times:
            response_times.sort()
            avg_response_time = sum(response_times) / len(response_times)
            p95_response_time = response_times[int(len(response_times) * 0.95)]
            p99_response_time = response_times[int(len(response_times) * 0.99)]
        else:
            avg_response_time = p95_response_time = p99_response_time = 0
        
        result = {
            'duration': actual_duration,
            'sent_requests': sent_requests,
            'completed_requests': completed_requests,
            'successful_requests': successful_requests,
            'rate_limited_requests': rate_limited_requests,
            'error_requests': error_requests,
            'actual_qps': actual_qps,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'p95_response_time': p95_response_time,
            'p99_response_time': p99_response_time
        }
        
        self.print_test_result(result)
        return result

    async def send_single_request(self, node_url, api_key, request_id):
        """发送单个请求并记录响应时间"""
        async with self.semaphore:
            start_time = time.time()
            try:
                async with self.session.post(
                    f"{node_url}/v1/chat/completions",
                    json={
                        "model": "gpt-4-turbo",
                        "messages": [{"role": "user", "content": f"test request {request_id}"}]
                    },
                    headers={"Authorization": f"Bearer {api_key}"}
                ) as response:
                    await response.read()
                    response_time = time.time() - start_time
                    return {
                        'status': response.status,
                        'response_time': response_time
                    }
                    
            except asyncio.TimeoutError:
                return {'status': 'timeout', 'response_time': time.time() - start_time}
            except Exception as e:
                return {'status': 'error', 'response_time': time.time() - start_time}

    def print_test_result(self, result):
        """打印测试结果"""
        print(f"\n📊 测试结果:")
        print(f"持续时间: {result['duration']:.2f} 秒")
        print(f"发送请求: {result['sent_requests']}")
        print(f"完成请求: {result['completed_requests']}")
        print(f"成功请求: {result['successful_requests']} (200)")
        print(f"限流请求: {result['rate_limited_requests']} (429)")
        print(f"错误请求: {result['error_requests']}")
        print(f"实际 QPS: {result['actual_qps']:.2f}")
        print(f"成功率: {result['success_rate']:.1f}%")
        print(f"平均响应时间: {result['avg_response_time']*1000:.1f}ms")
        print(f"P95 响应时间: {result['p95_response_time']*1000:.1f}ms")
        print(f"P99 响应时间: {result['p99_response_time']*1000:.1f}ms")

async def run_single_node_test():
    """运行单节点性能测试"""
    
    # 可配置的节点地址
    test_nodes = [
        "http://127.0.0.1:8003",
        "http://127.0.0.1:8004", 
        "http://127.0.0.1:8005"
    ]
    
    print("🔍 检查可用节点...")
    available_node = None
    
    # 检查节点可用性
    timeout = aiohttp.ClientTimeout(total=3)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for node in test_nodes:
            try:
                async with session.get(f"{node}/health") as response:
                    if response.status == 200:
                        available_node = node
                        print(f"✅ 选择节点: {node}")
                        break
                    else:
                        print(f"⚠️ {node} - 状态 {response.status}")
            except Exception as e:
                print(f"❌ {node} - 不可用")
    
    if not available_node:
        print("❌ 没有可用节点！")
        return
    
    # 测试配置
    test_configs = [
        {"name": "🚀 轻负载测试", "target_qps": 200, "duration": 8},
        {"name": "💪 中等负载测试", "target_qps": 500, "duration": 10},
        {"name": "⚡ 高负载测试", "target_qps": 800, "duration": 12},
        {"name": "🔥 极限负载测试", "target_qps": 1200, "duration": 15},
    ]
    
    api_key = "unlimited-key"
    
    try:
        async with SingleNodePerformanceClient(max_concurrency=600) as client:
            results = await client.single_node_stress_test(
                available_node, 
                api_key, 
                test_configs
            )
        
        # 分析最佳结果
        best_result = max(results, key=lambda x: x['result']['actual_qps'])
        
        print(f"\n🏆 单节点最佳性能:")
        print("=" * 50)
        print(f"最佳配置: {best_result['config']['name']}")
        print(f"🚀 最高 QPS: {best_result['result']['actual_qps']:.2f}")
        print(f"✅ 成功率: {best_result['result']['success_rate']:.1f}%")
        print(f"⚡ 平均响应时间: {best_result['result']['avg_response_time']*1000:.1f}ms")
        print(f"📊 总请求: {best_result['result']['completed_requests']}")
        
        # 性能评估
        best_qps = best_result['result']['actual_qps']
        if best_qps >= 1000:
            print("🎉 单节点超过1K QPS！")
        elif best_qps >= 800:
            print("👍 单节点性能优秀！")
        elif best_qps >= 500:
            print("👌 单节点性能良好")
        else:
            print("⚠️ 单节点性能有待提升")
        
        # 保存结果到文件
        with open('single_node_test_results.json', 'w', encoding='utf-8') as f:
            json.dump({
                'test_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'node_url': available_node,
                'api_key': api_key,
                'results': [
                    {
                        'config': r['config'],
                        'result': r['result']
                    } for r in results
                ],
                'best_performance': {
                    'config': best_result['config'],
                    'qps': best_result['result']['actual_qps'],
                    'success_rate': best_result['result']['success_rate']
                }
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 详细结果已保存到: single_node_test_results.json")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🎯 单节点性能测试启动")
    print("测试将逐步增加负载，找出单节点的性能极限")
    print("=" * 60)
    
    try:
        asyncio.run(run_single_node_test())
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
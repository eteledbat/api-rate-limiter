# distributed_performance_test.py
import asyncio
import aiohttp
import time
import random

async def test_distributed_performance():
    """测试三节点分布式性能"""
    
    nodes = [
        "http://127.0.0.1:8003",
        "http://127.0.0.1:8005", 
        "http://127.0.0.1:8004"
    ]
    
    # 先检查所有节点是否可用
    print("检查节点状态...")
    available_nodes = []
    
    async with aiohttp.ClientSession() as session:
        for node in nodes:
            try:
                async with session.get(f"{node}/health", timeout=3) as response:
                    if response.status == 200:
                        available_nodes.append(node)
                        print(f"✅ {node} - 可用")
                    else:
                        print(f"⚠️ {node} - 状态码 {response.status}")
            except:
                print(f"❌ {node} - 不可用")
    
    if len(available_nodes) == 0:
        print("没有可用节点！")
        return
    
    print(f"\n使用 {len(available_nodes)} 个节点进行测试")
    print(f"节点列表: {available_nodes}")
    
    # 分布式性能测试
    connector = aiohttp.TCPConnector(
        limit=500,
        limit_per_host=200,  # 每个节点最多200连接
        keepalive_timeout=30
    )
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=20)
    ) as session:
        
        semaphore = asyncio.Semaphore(len(available_nodes) * 50)  # 每节点50并发
        
        start_time = time.time()
        tasks = []
        
        # 总请求数：每个节点500个请求
        total_requests = len(available_nodes) * 500
        
        for i in range(total_requests):
            node = available_nodes[i % len(available_nodes)]  # 轮询分发
            task = send_distributed_request(session, semaphore, node, i)
            tasks.append(task)
        
        print(f"发送 {total_requests} 个请求到 {len(available_nodes)} 个节点...")
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        # 统计结果
        node_stats = {node: {"success": 0, "total": 0} for node in available_nodes}
        total_success = 0
        total_errors = 0
        
        for result in results:
            if isinstance(result, dict):
                node = result.get('node')
                if node in node_stats:
                    node_stats[node]["total"] += 1
                    if result.get('status') == 200:
                        node_stats[node]["success"] += 1
                        total_success += 1
                    elif result.get('status') == 429:
                        pass  # 限流，正常
                    else:
                        total_errors += 1
                else:
                    total_errors += 1
            else:
                total_errors += 1
        
        qps = len(results) / duration
        success_rate = total_success / len(results)
        
        print(f"\n分布式性能测试结果:")
        print(f"总请求: {len(results)}")
        print(f"成功请求: {total_success}")
        print(f"错误请求: {total_errors}")
        print(f"总 QPS: {qps:.2f}")
        print(f"成功率: {success_rate*100:.1f}%")
        print(f"耗时: {duration:.2f}秒")
        
        print(f"\n各节点统计:")
        for node, stats in node_stats.items():
            node_qps = stats["total"] / duration if duration > 0 else 0
            node_success_rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
            print(f"  {node}: {stats['success']}/{stats['total']} "
                  f"(QPS: {node_qps:.1f}, 成功率: {node_success_rate*100:.1f}%)")

async def send_distributed_request(session, semaphore, node, request_id):
    """发送分布式测试请求"""
    async with semaphore:
        try:
            async with session.post(
                f"{node}/v1/chat/completions",
                json={
                    "model": "gpt-4-turbo",
                    "messages": [{"role": "user", "content": "hi"}]
                },
                headers={"Authorization": "Bearer unlimited-key"}
            ) as response:
                return {"status": response.status, "node": node}
        except Exception as e:
            return {"error": str(e), "node": node}

if __name__ == "__main__":
    asyncio.run(test_distributed_performance())
import asyncio
import aiohttp
import time
import winloop

winloop.install()

async def extreme_load_test():
    """专门的1000 QPS极限测试"""
    
    nodes = [
        "http://127.0.0.1:8003",
        "http://127.0.0.1:8004", 
        "http://127.0.0.1:8005"
    ]
    
    print("🔥 极限负载测试 - 目标 1000 QPS")
    
    # 高性能连接配置
    connector = aiohttp.TCPConnector(
        limit=1000,            # 大幅提升连接数
        limit_per_host=500,    
        keepalive_timeout=60,  # 延长保持时间
        enable_cleanup_closed=True,
        use_dns_cache=True,
        ttl_dns_cache=600,
    )
    
    timeout = aiohttp.ClientTimeout(total=8, connect=1, sock_read=2)
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout
    ) as session:
        
        # 使用更高的并发信号量
        semaphore = asyncio.Semaphore(600)
        
        async def send_extreme_request(node, request_id):
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
                        await response.read()
                        return response.status
                except:
                    return "error"
        
        # 连续发送测试
        start_time = time.time()
        duration = 15  # 15秒测试
        target_qps = 1000
        
        sent_requests = 0
        active_tasks = []
        results = []
        
        print(f"开始 {target_qps} QPS 测试，持续 {duration} 秒...")
        
        while time.time() - start_time < duration:
            # 清理完成的任务
            finished = [task for task in active_tasks if task.done()]
            for task in finished:
                active_tasks.remove(task)
                try:
                    result = await task
                    results.append(result)
                except:
                    results.append("error")
            
            # 发送新请求
            if len(active_tasks) < 600:  # 控制活跃任务数
                node = nodes[sent_requests % len(nodes)]
                task = asyncio.create_task(
                    send_extreme_request(node, sent_requests)
                )
                active_tasks.append(task)
                sent_requests += 1
            
            # 控制发送速率
            await asyncio.sleep(1.0 / target_qps)
        
        # 等待剩余任务
        if active_tasks:
            remaining = await asyncio.gather(*active_tasks, return_exceptions=True)
            results.extend([r if not isinstance(r, Exception) else "error" for r in remaining])
        
        # 统计结果
        actual_duration = time.time() - start_time
        actual_qps = len(results) / actual_duration
        
        success_count = sum(1 for r in results if r == 200)
        rate_limited_count = sum(1 for r in results if r == 429)
        error_count = sum(1 for r in results if isinstance(r, str))
        
        print(f"\n🔥 极限测试结果:")
        print(f"实际 QPS: {actual_qps:.2f}")
        print(f"目标达成: {'✅' if actual_qps >= 900 else '❌'}")
        print(f"成功请求: {success_count}")
        print(f"限流请求: {rate_limited_count}")
        print(f"错误请求: {error_count}")
        print(f"成功率: {success_count/len(results)*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(extreme_load_test())
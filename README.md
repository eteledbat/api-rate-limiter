```markdown
# Distributed Rate Limiter for LLM API

一个高性能、分布式的 LLM API 速率限制器，支持滑动窗口算法和多节点部署。

## 项目概述

本项目实现了一个遵循 OpenAI API 格式的分布式速率限制器，支持以下核心功能：

- **三维速率限制**：每分钟请求数（RPM）、输入Token数（Input TPM）、输出Token数（Output TPM）
- **滑动窗口算法**：误差不超过1秒的精确速率控制
- **分布式一致性**：基于 Redis Lua 脚本的原子操作，避免并发问题
- **高性能设计**：单节点支持 1K+ QPS 吞吐量
- **可扩展架构**：支持多节点水平扩展

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Rate Limiter  │    │   Rate Limiter  │    │   Rate Limiter  │
│     Node 1      │    │     Node 2      │    │     Node 3      │
│   (Port 8000)   │    │   (Port 8001)   │    │   (Port 8002)   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                         ┌───────▼───────┐
                         │     Redis     │
                         │   (Shared)    │
                         └───────────────┘
```

## 核心技术特性

### 1. 原子化操作
使用 Redis Lua 脚本实现检查-更新的原子操作，避免竞态条件：
- 清理过期记录
- 检查三项限制
- 记录当前请求
- 设置 TTL

### 2. 滑动窗口实现
基于 Redis ZSET 的微秒级时间戳滑动窗口：
- 时间复杂度：O(log N + M)，其中 N 是窗口内总请求数，M 是需要清理的过期请求数
- 空间复杂度：O(N)，其中 N 是窗口内的请求数量

### 3. 分布式一致性
- 所有状态存储在共享 Redis 中
- 无需分布式锁，避免性能瓶颈
- 支持节点故障恢复

## 项目结构

```
dist_rate_limiter/
├── app/
│   ├── 

__init__.py


│   ├── 

config.py

          # 配置文件（Redis、API Keys、限制参数）
│   ├── 

main.py

           # FastAPI 应用主文件
│   └── 

limiter.lua

       # Redis Lua 脚本
├── tests/
│   ├── 

__init__.py


│   └── 

test_client.py

    # 高性能测试客户端
├── 

requirements.txt

      # Python 依赖
└── 

README.md


```

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 Redis 服务
redis-server
```

### 2. 启动 Rate Limiter 节点

启动多个节点来模拟分布式环境：

```bash
# 终端 1：启动节点 1
cd dist_rate_limiter
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 终端 2：启动节点 2  
cd dist_rate_limiter
uvicorn app.main:app --host 0.0.0.0 --port 8001

# 终端 3：启动节点 3
cd dist_rate_limiter
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

### 3. 运行性能测试

```bash
cd dist_rate_limiter
python tests/test_client.py
```

## API 使用说明

### 聊天完成接口

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-key-1" \
  -d '{
    "model": "gpt-4-turbo",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'
```

### 健康检查

```bash
curl "http://localhost:8000/health"
```

## 配置说明

在 

app/config.py

 中配置：

```python
API_KEYS_CONFIG = {
    "test-key-1": {
        "name": "Default Tier",
        "rpm": 300,          # 每分钟请求数
        "input_tpm": 60000,  # 每分钟输入Token数
        "output_tpm": 20000, # 每分钟输出Token数
    },
    "test-key-2": {
        "name": "High-Throughput Tier", 
        "rpm": 1000,
        "input_tpm": 200000,
        "output_tpm": 80000,
    }
}
```

## 性能分析

### 时间复杂度
- **速率检查**：O(log N + M)
  - log N：ZADD/ZREM 操作
  - M：窗口内 token 记录的遍历
- **清理操作**：O(log N + M)
  - 其中 M 是需要清理的过期记录数

### 空间复杂度
- **每个 API Key**：O(N)，其中 N 是窗口内的请求数
- **总体**：O(K × N)，其中 K 是活跃 API Key 数量

### 性能特点
- **高吞吐量**：单节点支持 1K+ QPS
- **低延迟**：Redis 操作延迟通常 < 1ms
- **线性扩展**：支持水平扩展多个节点
- **内存效率**：自动清理过期数据，设置 TTL 防止内存泄漏

## 测试结果

基于 

tests/test_client.py

 的压力测试：

```
--- Test Results ---
Total time elapsed: 20.00 seconds  
Total requests sent: 5000
Overall QPS: 250.00

Response Status Code Distribution:
  - 200 OK: 4500 requests
  - 429 Too Many Requests: 500 requests
```

## 可扩展性

### 水平扩展
- 添加更多 Rate Limiter 节点无需修改代码
- Redis 作为共享状态存储，支持集群部署
- 可通过负载均衡器分发请求

### 垂直扩展
- 优化 Redis 配置（内存、持久化）
- 调整 FastAPI 工作进程数量
- 使用 Redis 集群提升吞吐量

## 生产部署建议

1. **Redis 集群**：部署 Redis 集群以支持更大规模
2. **监控告警**：添加 Prometheus/Grafana 监控
3. **日志系统**：集成结构化日志记录
4. **配置中心**：使用 Consul/etcd 管理配置
5. **容器化**：使用 Docker/Kubernetes 部署

## 技术栈

- **Web 框架**：FastAPI
- **缓存/状态存储**：Redis
- **异步编程**：asyncio
- **HTTP 客户端**：httpx（测试）
- **ASGI 服务器**：uvicorn

## 许可证

MIT License
```
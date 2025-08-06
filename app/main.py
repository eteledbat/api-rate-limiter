import winloop
import asyncio
from fastapi import FastAPI, Request, HTTPException
import redis.asyncio as redis
import time
import random
from app.models import ChatCompletionRequest
from app.config import API_KEYS_CONFIG

# 🚀 在导入后立即设置事件循环策略
def setup_winloop():
    """设置Windows优化的事件循环"""
    try:
        # 设置winloop为默认事件循环
        winloop.install()
        print("✅ Winloop事件循环已安装")
    except Exception as e:
        print(f"⚠️ Winloop安装失败，使用默认事件循环: {e}")

# 立即设置事件循环
setup_winloop()

app = FastAPI(title="Windows High Performance Rate Limiter")

# Redis连接池配置
redis_pool = redis.ConnectionPool.from_url(
    "redis://localhost:6379",
    max_connections=500,         # Windows环境保守配置
    retry_on_timeout=True,
    socket_keepalive=True,
    socket_keepalive_options={
        1: 1,   # TCP_KEEPIDLE
        2: 3,   # TCP_KEEPINTVL  
        3: 5,   # TCP_KEEPCNT
    },
    health_check_interval=30
)

redis_client = redis.Redis(connection_pool=redis_pool)

# 全局变量
lua_limiter_script = None
WINDOW_SECONDS = 60

@app.on_event("startup")
async def startup_event():
    global lua_limiter_script
    
    print("🚀 启动Windows优化的Rate Limiter...")
  
    script_text = """
    local request_key = KEYS[1]
    local input_key = KEYS[2] 
    local output_key = KEYS[3]

    local current_time = tonumber(ARGV[1])
    local window_start = tonumber(ARGV[2])
    local rpm_limit = tonumber(ARGV[3])
    local input_tpm_limit = tonumber(ARGV[4])
    local output_tpm_limit = tonumber(ARGV[5])
    local input_tokens = tonumber(ARGV[6])
    local output_tokens = tonumber(ARGV[7])
    local request_id = ARGV[8]

    -- 🚀 使用计数器 + 定期校准的混合策略
    local req_counter = request_key .. ':counter'
    local input_counter = input_key .. ':counter'
    local output_counter = output_key .. ':counter'
    local last_sync = request_key .. ':last_sync'

    -- 检查是否需要同步校准（每30秒一次）
    local sync_time = tonumber(redis.call('GET', last_sync) or 0)
    local need_sync = (current_time - sync_time) > 30

    if need_sync then
        -- 🚀 定期校准：重新计算精确值
        redis.call('ZREMRANGEBYSCORE', request_key, '-inf', window_start)
        redis.call('ZREMRANGEBYSCORE', input_key, '-inf', window_start)
        redis.call('ZREMRANGEBYSCORE', output_key, '-inf', window_start)
        
        -- 重新统计精确计数
        local exact_requests = redis.call('ZCARD', request_key)
        local exact_input = 0
        local exact_output = 0
        
        -- 重新计算token数量
        local input_members = redis.call('ZRANGEBYSCORE', input_key, window_start, '+inf')
        for _, member in ipairs(input_members) do
            local tokens = tonumber(string.match(member, ':(%d+)$'))
            exact_input = exact_input + (tokens or 1)
        end
        
        local output_members = redis.call('ZRANGEBYSCORE', output_key, window_start, '+inf')
        for _, member in ipairs(output_members) do
            local tokens = tonumber(string.match(member, ':(%d+)$'))
            exact_output = exact_output + (tokens or 1)
        end
        
        -- 重置计数器为精确值
        redis.call('SET', req_counter, exact_requests)
        redis.call('SET', input_counter, exact_input)
        redis.call('SET', output_counter, exact_output)
        redis.call('SET', last_sync, current_time)
        
        -- 设置过期时间
        redis.call('EXPIRE', req_counter, 90)
        redis.call('EXPIRE', input_counter, 90)
        redis.call('EXPIRE', output_counter, 90)
        redis.call('EXPIRE', last_sync, 90)
    else
        -- 🚀 高速模式：使用计数器
        -- 获取当前计数
        local current_requests = tonumber(redis.call('GET', req_counter) or 0)
        local current_input_tokens = tonumber(redis.call('GET', input_counter) or 0)
        local current_output_tokens = tonumber(redis.call('GET', output_counter) or 0)
        
        -- 检查限制
        if current_requests >= rpm_limit then
            return {0, 'RPM_EXCEEDED'}
        end
        
        if current_input_tokens + input_tokens > input_tpm_limit then
            return {0, 'INPUT_TPM_EXCEEDED'}
        end
        
        if current_output_tokens + output_tokens > output_tpm_limit then
            return {0, 'OUTPUT_TPM_EXCEEDED'}
        end
        
        -- 快速更新计数器
        redis.call('INCR', req_counter)
        if input_tokens > 0 then
            redis.call('INCRBY', input_counter, input_tokens)
        end
        if output_tokens > 0 then
            redis.call('INCRBY', output_counter, output_tokens)
        end
        
        -- 同时维护精确记录（用于校准）
        redis.call('ZADD', request_key, current_time, request_id)
        if input_tokens > 0 then
            redis.call('ZADD', input_key, current_time, request_id .. ':in:' .. input_tokens)
        end
        if output_tokens > 0 then
            redis.call('ZADD', output_key, current_time, request_id .. ':out:' .. output_tokens)
        end
    end

    -- 设置基础数据过期时间
    redis.call('EXPIRE', request_key, 3600)
    redis.call('EXPIRE', input_key, 3600)
    redis.call('EXPIRE', output_key, 3600)

    return {1, 'ALLOWED'}
    """
    
    try:
        lua_limiter_script = redis_client.register_script(script_text)
        print("✅ 高性能Lua脚本已加载")
    except Exception as e:
        print(f"❌ Lua脚本加载失败: {e}")

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy", 
        "timestamp": time.time(),
        "event_loop": str(type(asyncio.get_event_loop())),
        "redis_pool_size": redis_pool.connection_kwargs.get('max_connections', 'unknown')
    }

async def check_rate_limit_fast(api_key: str, input_tokens: int, output_tokens: int) -> tuple[bool, str]:
    """高性能速率限制检查"""
    config = API_KEYS_CONFIG.get(api_key)
    if not config:
        return True, "INVALID_API_KEY"

    keys = [
        f"rl:{api_key}:req",
        f"rl:{api_key}:input",
        f"rl:{api_key}:output"
    ]
    
    current_time_us = int(time.time() * 1_000_000)
    window_start_us = current_time_us - (WINDOW_SECONDS * 1_000_000)
    request_id = f"{current_time_us}{random.randint(100, 999)}"

    args = [
        current_time_us,
        window_start_us,
        config["rpm"],
        config["input_tpm"], 
        config["output_tpm"],
        input_tokens,
        output_tokens,
        request_id
    ]

    try:
        result = await lua_limiter_script(keys=keys, args=args)
        is_allowed = result[0] == 1
        reason = result[1] if len(result) > 1 else "UNKNOWN"
        return not is_allowed, reason
    except Exception as e:
        print(f"Rate limit check error: {e}")
        return True, "SYSTEM_ERROR"

@app.post("/v1/chat/completions")
async def chat_completions(request: Request, body: ChatCompletionRequest):
    """高性能chat completions端点"""
    
    # 快速认证
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    
    api_key = auth_header[7:]  # 去掉 "Bearer "

    # 快速token估算
    total_chars = sum(len(msg.content) for msg in body.messages) if body.messages else 0
    input_tokens = max(1, total_chars // 4)  # 粗略估算：4字符=1token
    output_tokens = 50  # 固定输出避免随机开销

    # 速率限制检查
    is_blocked, reason = await check_rate_limit_fast(api_key, input_tokens, output_tokens)
    if is_blocked:
        raise HTTPException(
            status_code=429, 
            detail=f"Rate limit exceeded: {reason}",
            headers={"Retry-After": "60"}
        )

    # 快速响应生成
    timestamp = int(time.time())
    response_id = f"chatcmpl-{timestamp:x}"
    
    return {
        "id": response_id,
        "object": "chat.completion",
        "created": timestamp,
        "model": body.model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "High-performance Windows mock response!"
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    print("🪟 启动Windows优化服务器...")
    
    # Windows优化的uvicorn配置
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8003,
        workers=1,
        access_log=False,  # 关闭访问日志提高性能
        server_header=False,  # 不发送服务器头信息
        date_header=False,  # 不发送日期头信息
    )